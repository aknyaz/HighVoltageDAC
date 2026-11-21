"""Exercise real mute RTL, reference arithmetic, branch timing and fault priority."""
import csv,json,random
from fractions import Fraction
from pathlib import Path
from amaranth.sim import Simulator
from mute_controller import MuteController
ROOT=Path(__file__).resolve().parents[1]
MASK=(1<<32)-1

def decode(a,b):
    def arm(x):return (x%512)|sum(1<<(9+i) for i in range(7) if x>=(i+1)*512)
    return arm(a)|(arm(b)<<16)

def rounded(x):return (2*x.numerator+x.denominator)//(2*x.denominator)

def reference(pcm,g,c,n):
    center=Fraction(4095,2)*Fraction(c,n)
    swing=Fraction(4095,2)*Fraction(pcm,1<<23)*Fraction(g,n)
    return rounded(center+swing),rounded(center-swing)

class Harness:
    def __init__(self,ctx,d):self.ctx=ctx;self.d=d;self.samples=0;self.checks=0;self.g=0;self.c=0;self.rows=[]
    async def tick(self,count=1):
        if count==1:await self.ctx.tick()
        else:await self.ctx.tick().repeat(count)
        assert self.ctx.get(self.d.h)&self.ctx.get(self.d.l)==0
        self.checks+=1
    async def start(self):
        c=self.ctx;d=self.d
        c.set(d.reset_n,0);c.set(d.valid,0);c.set(d.arm,0);c.set(d.run,0)
        c.set(d.ready,1);c.set(d.fault_n,1);await self.tick()
        c.set(d.reset_n,1);await self.tick();c.set(d.run,1);c.set(d.arm,1);await self.tick();c.set(d.arm,0)
        self.g=self.c=0
        assert c.get(d.enable) and not c.get(d.muted)
        assert c.get(d.h)==c.get(d.l)==0
    async def sample(self,mute,pcm=0,period=12,record=False):
        c=self.ctx;d=self.d;n=d.ramp_samples
        if mute:
            if self.g:self.g-=1
            elif self.c:self.c-=1
        else:
            if self.c<n:self.c+=1
            elif self.g<n:self.g+=1
        a,b=reference(pcm,self.g,self.c,n)
        c.set(d.mute,mute);c.set(d.pcm,pcm);c.set(d.valid,1)
        await c.delay(1e-10)
        assert (c.get(d.code_a),c.get(d.code_b))==(a,b),(pcm,self.g,self.c,a,b,c.get(d.code_a),c.get(d.code_b))
        h=c.get(d.h);l=c.get(d.l);target=decode(a,b);changed=(h^target)|(l^(target^MASK))
        await self.tick();c.set(d.valid,0)
        assert (c.get(d.gain_step),c.get(d.common_step))==(self.g,self.c)
        assert (c.get(d.h),c.get(d.l))==(h&~changed,l&~changed)
        if changed:assert not c.get(d.muted)
        for _ in range(d.core.dead_cycles):
            assert (c.get(d.h)&changed)==(c.get(d.l)&changed)==0
            await self.tick()
        assert (c.get(d.h),c.get(d.l))==(target,target^MASK)
        assert not c.get(d.busy) and not c.get(d.fault)
        assert c.get(d.muted)==int(self.g==self.c==0)
        if self.c<n:assert a==b
        if record:self.rows.append([self.samples,pcm,int(mute),self.g,self.c,a,b,target,target^MASK])
        await self.tick(period-d.core.dead_cycles-1)
        self.samples+=1

async def normal(ctx,d,report):
    h=Harness(ctx,d);await h.start();n=d.ramp_samples;rng=random.Random(20261116)
    index=0
    async def sample(mute,pcm):
        nonlocal index
        # Successive rounded 50 MHz clock timestamps for a 192 kS/s stream.
        period=round((index+1)*50e6/192000)-round(index*50e6/192000)
        await h.sample(mute,pcm,period,True);index+=1
    for _ in range(2*n):await sample(False,rng.randrange(-(1<<23),1<<23))
    assert h.g==h.c==n
    for pcm in (-(1<<23),-1,0,1,(1<<23)-1):await sample(False,pcm)
    for _ in range(2*n):await sample(True,rng.randrange(-(1<<23),1<<23))
    assert ctx.get(d.muted)
    # Park longer than the 1 ms watchdog while supervised refresh continues.
    for _ in range(220):await sample(True,(1<<23)-1)
    assert ctx.get(d.h)==0 and ctx.get(d.l)==MASK and not ctx.get(d.fault)
    # Missing refresh must still trip while parked.
    await h.tick(d.core.timeout_cycles+2)
    assert ctx.get(d.fault) and not ctx.get(d.enable) and not ctx.get(d.muted)
    report.update(default_samples=h.samples,nonoverlap_and_timing_checks=h.checks,
        ramp_samples=n,ramp_ms_at_192ksps=1000*n/192000,quiet_refresh_samples=220,
        default_watchdog_cycles=d.core.timeout_cycles)
    out=ROOT/'results/control';out.mkdir(exist_ok=True,parents=True)
    with (out/'mute_commands.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['sample','pcm24','mute','gain_step','common_step','code_a','code_b','settled_high','settled_low']);w.writerows(h.rows)

async def edge_cases(ctx,d,report):
    h=Harness(ctx,d);n=d.ramp_samples
    await h.start()
    # Reverse each partial common-mode and gain ramp in both directions.
    for command,count in ((False,3),(True,2),(False,n+3),(True,2),(False,n),(True,n+3),(False,2),(True,2*n)):
        for i in range(count):await h.sample(command,(-(1<<23),0,(1<<23)-1)[i%3])
    assert ctx.get(d.muted)
    fault_tests=0
    for phase in ('park','up','fade_in','play','fade_out','down'):
        for fault in ('fault_n','ready','run','reset_n','timeout','busy_request'):
            await h.start()
            await h.sample(True)
            if phase!='park':
                for _ in range({'up':3,'fade_in':n+3,'play':2*n,'fade_out':2*n,'down':2*n}[phase]):await h.sample(False,7000000)
                if phase in ('fade_out','down'):
                    for _ in range(3 if phase=='fade_out' else n+3):await h.sample(True,7000000)
            if fault=='timeout':
                await h.tick(d.core.timeout_cycles+2)
                assert ctx.get(d.fault)
            elif fault=='busy_request':
                # Opposite mute direction guarantees a different target here.
                ctx.set(d.mute,not (phase in ('park','down','fade_out')))
                ctx.set(d.pcm,-7000000);ctx.set(d.valid,1);await h.tick()
                assert ctx.get(d.busy)
                await h.tick();ctx.set(d.valid,0);assert ctx.get(d.fault)
            else:
                # Assert the raw disable in the middle of a real blank interval.
                ctx.set(d.mute,not (phase in ('park','down','fade_out')))
                ctx.set(d.pcm,-7000000);ctx.set(d.valid,1);await h.tick()
                ctx.set(d.valid,0);assert ctx.get(d.busy)
                ctx.set(getattr(d,fault),0);await ctx.delay(1e-9)
                assert ctx.get(d.h)==ctx.get(d.l)==ctx.get(d.enable)==0
                await h.tick()
                if fault in ('ready','fault_n'):assert ctx.get(d.fault)
            assert ctx.get(d.h)==ctx.get(d.l)==0 and not ctx.get(d.muted)
            # Restore external conditions without reset/clear/arm: no auto restart.
            if fault in ('fault_n','ready','run','reset_n'):
                ctx.set(getattr(d,fault),1);await h.tick();assert not ctx.get(d.enable)
            fault_tests+=1
    report.update(reversal_and_fault_samples=h.samples,additional_timing_checks=h.checks,
        phase_fault_cases=fault_tests,phases=['park','up','fade_in','play','fade_out','down'])

def main():
    report={}
    for d,bench in ((MuteController(),normal),(MuteController(ramp_samples=8,timeout_cycles=100),edge_cases)):
        sim=Simulator(d);sim.add_clock(20e-9)
        async def run(ctx):await bench(ctx,d,report)
        sim.add_testbench(run);sim.run()
    report['scope']='Executed Amaranth RTL; not routed FPGA timing, analog co-simulation or hardware validation.'
    (ROOT/'results/control/mute_verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS',report,flush=True)
if __name__=='__main__':main()
