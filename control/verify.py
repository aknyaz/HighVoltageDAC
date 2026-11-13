"""Execute HDL simulation, independent decoding and non-overlap assertions."""
from pathlib import Path
import json,random
from amaranth.sim import Simulator
from controller import Controller
ROOT=Path(__file__).resolve().parents[1]
def decode(code):
    def arm(x):return (x&511)|(((1<<(x//512))-1)<<9)
    return arm(code)|(arm(4095-code)<<16)
async def bench(ctx,d,report):
    checks=0;cycles=0
    async def tick():
        nonlocal checks,cycles
        await ctx.tick();cycles+=1
        assert ctx.get(d.h)&ctx.get(d.l)==0
        checks+=1
    async def start():
        ctx.set(d.run,0);ctx.set(d.clear,1);ctx.set(d.ready,1);ctx.set(d.fault_n,1);await tick()
        ctx.set(d.clear,0);ctx.set(d.arm,0);await tick();ctx.set(d.run,1);ctx.set(d.arm,1);await tick();ctx.set(d.arm,0)
        assert ctx.get(d.enable)
    ctx.set(d.reset_n,0);await tick();ctx.set(d.reset_n,1);await tick()
    assert ctx.get(d.h)==ctx.get(d.l)==0
    await start()
    rng=random.Random(20261110)
    codes=list(range(4096))+[rng.randrange(4096) for _ in range(1000)]
    previous=None
    for code in codes:
        h0=ctx.get(d.h);l0=ctx.get(d.l);target=decode(code);mask=(1<<32)-1
        changed=(h0^target)|(l0^(target^mask))
        ctx.set(d.code,code);ctx.set(d.valid,1);await tick();ctx.set(d.valid,0)
        assert ctx.get(d.h)==(h0&~changed) and ctx.get(d.l)==(l0&~changed)
        for i in range(10):
            if changed:
                assert ctx.get(d.h)&changed==0 and ctx.get(d.l)&changed==0
            await tick()
        assert ctx.get(d.h)==target and ctx.get(d.l)==(target^mask)
        assert not ctx.get(d.busy) and not ctx.get(d.fault)
        previous=code
    # Asynchronous combinational mask plus clocked fault latch.
    for signal in (d.fault_n,d.ready):
        ctx.set(signal,0);await ctx.delay(1e-9)
        assert ctx.get(d.h)==ctx.get(d.l)==ctx.get(d.enable)==0
        await tick();assert ctx.get(d.fault)
        ctx.set(signal,1);await tick();assert not ctx.get(d.enable)
        await start()
    # Overspeed request is latched as a protocol fault.
    ctx.set(d.valid,1);await tick();await tick();ctx.set(d.valid,0)
    assert ctx.get(d.fault) and not ctx.get(d.enable)
    await start()
    # Held code requires a fresh valid heartbeat before the timeout.
    for _ in range(d.timeout_cycles+2):await tick()
    assert ctx.get(d.fault) and not ctx.get(d.enable)
    await start();ctx.set(d.reset_n,0);await ctx.delay(1e-9)
    assert ctx.get(d.h)==ctx.get(d.l)==0
    ctx.set(d.reset_n,1);await start()
    ctx.set(d.valid,1);await tick();ctx.set(d.valid,0)
    ctx.set(d.run,0);await ctx.delay(1e-9);assert ctx.get(d.h)==ctx.get(d.l)==0
    await tick();ctx.set(d.run,1);await tick();assert not ctx.get(d.enable)
    # Shared schematic nets must match the independent HDL channel ordering.
    import xml.etree.ElementTree as ET
    netlist=ET.parse(ROOT/'results/segmented_review/netlist.xml')
    nets={(p.get('ref'),p.get('pin')):n.get('code') for n in netlist.findall('.//nets/net') for p in n.findall('node')}
    for i in range(32):
        assert nets[f'U{2*i+1}','10']==nets['X900',f'H{i}']
        assert nets[f'U{2*i+2}','10']==nets['X900',f'L{i}']
    for i in range(64):
        assert nets[f'U{i+1}','14']==nets['X900','ENABLE']
        assert nets[f'U{i+1}','12']==nets['X900','RDY_ALL']
        assert nets[f'U{i+1}','13']==nets['X900','FLT_N']
    report.update(codes_tested=len(codes),cycles_checked=cycles,nonoverlap_checks=checks,
                  dead_cycles=10,clock_hz=50000000,nominal_dead_ns=200,
                  schematic_command_paths_checked=64,schematic_shared_status_paths_checked=192,
                  tested_faults=['fault input','ready loss','sample while busy','missing sample timeout','reset','run dropped while busy'],
                  scope='Behavioral HDL simulation, not routed FPGA timing or transistor turn-off verification')

if __name__=='__main__':
    # Short watchdog in tests keeps timeout tests quick; production default is 1 ms.
    d=Controller(timeout_cycles=100);report={};sim=Simulator(d);sim.add_clock(20e-9)
    async def run(ctx):await bench(ctx,d,report)
    sim.add_testbench(run);sim.run()
    out=ROOT/'results/control';out.mkdir(parents=True,exist_ok=True)
    (out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
