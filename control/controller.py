"""Synthesizable 3+9 command sequencer; hardware timing/CDC wrapper still required."""
from amaranth import *
from amaranth.back import verilog
from pathlib import Path

class Controller(Elaboratable):
    def __init__(self,dead_cycles=10,timeout_cycles=50000):
        assert dead_cycles>=1 and timeout_cycles>dead_cycles
        self.dead_cycles=dead_cycles;self.timeout_cycles=timeout_cycles
        self.code=Signal(12);self.code_b=Signal(12);self.independent=Signal();self.valid=Signal();self.arm=Signal();self.run=Signal()
        self.ready=Signal();self.fault_n=Signal();self.clear=Signal();self.reset_n=Signal()
        self.h=Signal(32);self.l=Signal(32);self.enable=Signal();self.busy=Signal();self.fault=Signal()
    def elaborate(self,platform):
        m=Module();m.domains.sync=ClockDomain(async_reset=True)
        m.d.comb+=ResetSignal().eq(~self.reset_n)
        active=Signal();pending=Signal(32);hi=Signal(32);lo=Signal(32)
        countdown=Signal(range(self.dead_cycles+1));age=Signal(range(self.timeout_cycles+1))
        arm_old=Signal();m.d.sync+=arm_old.eq(self.arm)
        b=Signal(12);target=Signal(32)
        m.d.comb += [b.eq(Mux(self.independent,self.code_b,4095-self.code)),target.eq(Cat(self.code[:9],*[self.code[9:]>i for i in range(7)],b[:9],*[b[9:]>i for i in range(7)])),
                     self.busy.eq(countdown!=0),self.enable.eq(active & self.run & self.ready & self.fault_n & ~self.fault & self.reset_n),
                     self.h.eq(Mux(self.enable,hi,0)),self.l.eq(Mux(self.enable,lo,0))]
        with m.If(~self.fault_n | (active & ~self.ready) | (active & self.valid & self.busy) | (active & (age==self.timeout_cycles))):
            m.d.sync += [self.fault.eq(1),active.eq(0),hi.eq(0),lo.eq(0),countdown.eq(0),age.eq(0)]
        with m.Elif(~self.run):
            m.d.sync += [active.eq(0),hi.eq(0),lo.eq(0),countdown.eq(0),age.eq(0)]
            with m.If(self.clear & self.fault_n & self.ready):m.d.sync+=self.fault.eq(0)
        with m.Elif(self.fault):
            m.d.sync += [active.eq(0),hi.eq(0),lo.eq(0),countdown.eq(0)]
        with m.Elif(~active):
            with m.If(self.arm & ~arm_old & self.ready):m.d.sync += [active.eq(1),age.eq(0)]
        with m.Else():
            m.d.sync += age.eq(age+1)
            with m.If(self.valid):
                # Disable changing branches; leave unchanged branches conducting.
                same=(hi==target) & (lo==~target)
                changed=(hi ^ target) | (lo ^ ~target)
                m.d.sync += [age.eq(0),pending.eq(target)]
                with m.If(~same):m.d.sync += [hi.eq(hi & ~changed),lo.eq(lo & ~changed),countdown.eq(self.dead_cycles)]
            with m.Elif(countdown>1):m.d.sync+=countdown.eq(countdown-1)
            with m.Elif(countdown==1):m.d.sync += [hi.eq(pending),lo.eq(~pending),countdown.eq(0)]
        return m

def ports(d):return [d.code,d.code_b,d.independent,d.valid,d.arm,d.run,d.ready,d.fault_n,d.clear,d.reset_n,d.h,d.l,d.enable,d.busy,d.fault]
if __name__=='__main__':
    d=Controller();p=Path(__file__).parent/'generated';p.mkdir(exist_ok=True)
    (p/'rdac_control.v').write_text(verilog.convert(d,name='rdac_control',ports=ports(d)))
    print('Generated',p/'rdac_control.v')
