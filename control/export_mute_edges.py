"""Export timestamped gate vectors from executed mute RTL for analog replay."""
import csv,json,math
from pathlib import Path
from amaranth.sim import Simulator
from mute_controller import MuteController
from verify_mute import Harness
ROOT=Path(__file__).resolve().parents[1]

class Recorder(Harness):
    def __init__(self,ctx,d):
        super().__init__(ctx,d);self.cycle=0;self.edges=[[0,0,0]]
    async def tick(self,count=1):
        await super().tick(count);self.cycle+=count
        pair=[self.ctx.get(self.d.h),self.ctx.get(self.d.l)]
        if pair!=self.edges[-1][1:]:self.edges.append([self.cycle,*pair])

async def bench(ctx,d,report):
    h=Recorder(ctx,d);await h.start();commands=[[0,0,0]]
    for i in range(2688):
        t=i/192000
        pcm=round(.9*((1<<23)-1)*math.cos(2*math.pi*1000*t))
        mute=960<=i<1920  # 5 ms request, 10 ms resume.
        period=round((i+1)*50e6/192000)-round(i*50e6/192000)
        request=h.cycle+1
        await h.sample(mute,pcm,period,True)
        commands.append([request,h.rows[-1][5],h.rows[-1][6]])
    assert h.g==h.c==384 and not ctx.get(d.fault)
    # No commands change during the settled, supervised 9-10 ms quiet hold.
    q0=commands[1728][0]+10;q1=commands[1921][0]
    assert not any(q0<c<q1 for c,_,_ in h.edges)
    for c,hi,lo in h.edges:assert hi&lo==0
    out=ROOT/'results/rtl_replay';out.mkdir(exist_ok=True,parents=True)
    for filename,header,rows in [('gate_edges.csv',['cycle','high','low'],h.edges),
                               ('code_commands.csv',['cycle','code_a','code_b'],commands)]:
        with (out/filename).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
    report.update(samples=h.samples,clock_hz=50000000,sample_rate_hz=192000,
        stop_cycle=h.cycle+1,gate_vector_events=len(h.edges)-1,checks=h.checks,
        mute_request_sample=960,resume_request_sample=1920,
        quiet_gate_transitions=0,origin='cycle zero is one clock period before the first recorded tick',
        scope='Executed RTL gate vectors, nominal command timing; no physical FPGA propagation delays.')

def main():
    d=MuteController();sim=Simulator(d);sim.add_clock(20e-9);report={}
    async def run(ctx):await bench(ctx,d,report)
    sim.add_testbench(run);sim.run()
    (ROOT/'results/rtl_replay/export.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS',report,flush=True)
if __name__=='__main__':main()
