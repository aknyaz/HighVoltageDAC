"""Ideal transformer and Thevenin calculations; not a full DAC loss model."""
import json
from math import sqrt


def calculate(power_w=5, load_ohm=8, primary_ohm=5000,
              source_ohm=5000, source_peak_v=500):
    if min(power_w, load_ohm, primary_ohm) <= 0 or min(source_ohm, source_peak_v) < 0:
        raise ValueError('Positive loads/power and nonnegative source values required')
    attenuation = primary_ohm / (primary_ohm + source_ohm)
    return dict(power_w=power_w, turns_ratio=sqrt(primary_ohm/load_ohm),
                secondary_rms_v=sqrt(power_w*load_ohm),
                primary_rms_v=sqrt(power_w*primary_ohm),
                primary_peak_v=sqrt(2*power_w*primary_ohm),
                primary_rms_a=sqrt(power_w/primary_ohm),
                attenuation=attenuation,
                required_source_peak_v=sqrt(2*power_w*primary_ohm)/attenuation,
                equivalent_series_loss_w=power_w*source_ohm/primary_ohm,
                attainable_sine_power_w=(source_peak_v*attenuation)**2/(2*primary_ohm))


if __name__ == '__main__':
    print(json.dumps([calculate(power_w=p) for p in (5, 10)], indent=2))
