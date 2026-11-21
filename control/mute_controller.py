"""Sample-driven mute envelope and independent-arm targets for the 3+9 core.

24-bit signed PCM; 384 accepted samples per ramp at 192 kS/s = 2 ms.
Constant integer division is synthesizable but FPGA area/timing are not qualified.
"""
from pathlib import Path
from amaranth import *
from amaranth.back import verilog
from controller import Controller

class MuteController(Elaboratable):
    def __init__(self, ramp_samples=384, dead_cycles=10, timeout_cycles=50000):
        assert ramp_samples>=2
        self.ramp_samples=ramp_samples
        self.core=Controller(dead_cycles,timeout_cycles)
        self.pcm=Signal(signed(24));self.mute=Signal()
        for name in ('valid','arm','run','ready','fault_n','clear','reset_n',
                     'h','l','enable','busy','fault'):
            setattr(self,name,getattr(self.core,name))
        self.gain_step=Signal(range(ramp_samples+1))
        self.common_step=Signal(range(ramp_samples+1))
        self.code_a=Signal(12);self.code_b=Signal(12);self.muted=Signal()

    def elaborate(self,platform):
        m=Module();m.submodules.core=d=self.core
        n=self.ramp_samples
        ng=Signal.like(self.gain_step);nc=Signal.like(self.common_step)
        m.d.comb += [ng.eq(self.gain_step),nc.eq(self.common_step)]
        # Reversals retrace the current ramp; no phase-boundary jump.
        with m.If(self.mute):
            with m.If(self.gain_step>0):m.d.comb+=ng.eq(self.gain_step-1)
            with m.Elif(self.common_step>0):m.d.comb+=nc.eq(self.common_step-1)
        with m.Else():
            with m.If(self.common_step<n):m.d.comb+=nc.eq(self.common_step+1)
            with m.Elif(self.gain_step<n):m.d.comb+=ng.eq(self.gain_step+1)
        with m.If(~d.enable):
            m.d.sync += [self.gain_step.eq(0),self.common_step.eq(0)]
        with m.Elif(self.valid & ~d.busy):
            m.d.sync += [self.gain_step.eq(ng),self.common_step.eq(nc)]

        # Round each arm independently, half upward. Envelope precedes 12-bit
        # quantization. Exact midpoint is 2047.5, so zero PCM maps to 2048/2048.
        base=(1<<23)*n
        width=(2*base).bit_length()
        product=Signal(signed(width+1))
        positive=Signal(width);negative=Signal(width)
        audio_a=Signal(12);audio_b=Signal(12);common_code=Signal(12)
        m.d.comb += [product.eq(self.pcm*ng),positive.eq(base+product),negative.eq(base-product),
            audio_a.eq((positive*4095+base)//(2*base)),
            audio_b.eq((negative*4095+base)//(2*base)),
            common_code.eq((4095*nc+n)//(2*n)),
            self.code_a.eq(Mux(nc<n,common_code,audio_a)),
            self.code_b.eq(Mux(nc<n,common_code,audio_b)),
            d.independent.eq(1),d.code.eq(self.code_a),d.code_b.eq(self.code_b),
            self.muted.eq(d.enable & ~d.busy & (self.gain_step==0) &
                          (self.common_step==0) & (d.h==0) & (d.l==0xffffffff))]
        return m

def ports(d):
    return [getattr(d,n) for n in ('pcm','mute','valid','arm','run','ready','fault_n','clear',
        'reset_n','h','l','enable','busy','fault','muted','gain_step','common_step','code_a','code_b')]

if __name__=='__main__':
    d=MuteController();p=Path(__file__).parent/'generated';p.mkdir(exist_ok=True)
    (p/'rdac_mute_control.v').write_text(verilog.convert(d,name='rdac_mute_control',ports=ports(d)))
    print('Generated',p/'rdac_mute_control.v')
