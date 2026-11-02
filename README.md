# DTSU666 Sniffer (Deye / Chint)

Home Assistant custom integration that **listens in** on the RS485 bus between a Deye
inverter and its Chint DTSU666 energy meter, through an RS485-to-Ethernet gateway
(tested with a Waveshare *2-CH RS485 TO POE ETH (B)*).

The Deye polls the meter about 7 times per second for the power per phase and the
energy counters. This integration reads those answers, so Home Assistant gets the same
fast data without adding load to the bus.

## What you get

| Sensor | Source | Update rate |
|---|---|---|
| Power L1 / L2 / L3 / total | Deye's own requests (listen only) | ~7× per second |
| Energy import / export (kWh) | Deye's own requests (listen only) | ~0.7× per second |
| Voltage L1 / L2 / L3 | one own request, right after a Deye answer | every 60 s (configurable, 0 = never) |
| Current L1 / L2 / L3 (fast), highest phase | `|P| / U` with the last measured voltage | ~7× per second |
| Current L1 / L2 / L3 (measured) | switch *Ask for current* on: own request | every 1 s (configurable) |

Entity names are in Dutch (*Vermogen*, *Spanning*, *Stroom*, *Stroom hoogste fase*,
switch *Stroom zelf meevragen*).

### Current from power

A fuse reacts to current, not power. Without asking the meter, current is derived as
`I = |P| / U`. That is a lower bound: the real current is `|P| / (U × PF)`, so with a
low power factor the real current is higher. For heavy resistive loads (PF ≈ 1, e.g.
instantaneous water heaters) it is accurate.

Turn on the switch **Stroom zelf meevragen** when you need exact current: the
integration then asks the meter for voltage and current every second, and the fast
current sensors start from the measured current and follow the power changes in
between (`I = I_measured + Δ|P| / U`). The switch is off after every restart.

### Bus safety

Own requests are sent right after the meter answered the Deye, when the bus is idle.
Measured on a live system (40 s, one request per second): the Deye missed 3 of 302
answers with our requests and 7 of 317 without, i.e. no measurable effect.

## Gateway setup

Either gateway mode works:

* **Modbus TCP** (Waveshare protocol "Modbus TCP to RTU"): the gateway forwards the
  bus traffic to connected TCP clients as Modbus TCP frames.
* **Transparent** (protocol "None"): raw RTU frames with CRC are forwarded.

The integration detects the format by itself. The meter address is usually 1.

## Installation

HACS: add this repository as a custom repository (category *Integration*), install,
restart Home Assistant.

Manual: copy `custom_components/dtsu666_sniffer` to `config/custom_components/`
and restart.

Then *Settings → Devices & services → Add integration → DTSU666 Sniffer*.

| Option | Meaning |
|---|---|
| Gateway IP / TCP port | RS485 gateway, usually port 502 |
| Mode | `sniff` (listen to the Deye) or `poll` (no Deye on the bus: ask everything yourself) |
| Meter address | Modbus address of the DTSU666 (default 1) |
| Current interval | seconds between current requests while the switch is on |
| Voltage interval | seconds between voltage requests (0 = never) |
| Voltage sensors L1-L3 | optional HA sensors used until the first voltage is measured (fallback 230 V) |

## Registers (DTSU666, float32 big-endian, holding registers)

`0x2000` Uab … `0x2006` Ua … `0x200C` Ia … `0x2012` Pt, `0x2014` Pa … `0x202A` PFt …
`0x2044` frequency, `0x101E` import kWh, `0x1028` export kWh. See `const.py`.

## License

MIT
