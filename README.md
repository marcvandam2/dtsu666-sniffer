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
| Current L1 / L2 / L3 (fast) | `|P| / U` with the last measured voltage | ~7× per second |
| Current L1 / L2 / L3 (measured) | switch *Ask for current* on: own request | every 1 s (configurable) |

Entities: *Power L1-L3 / total*, *Energy import / export*, *Voltage L1-L3*,
*Current L1-L3 (fast)*, *Current L1-L3* (measured), and the
switch *Ask meter for current*.

### Sign and update rate

*Current L1-L3 (fast)* carries the sign of the power: positive = import, negative =
export (like a DSMR/P1 meter), so automations can use `above: 24` and `below: -24`.

The bus delivers ~7 readings per second. To keep the recorder database small, a sensor
writes its state at most once per second, except immediately on a jump of at least
1 A (current) or 250 W (power), so a heavy load switching on is seen at once.

### Current from power

A fuse reacts to current, not power. Without asking the meter, current is derived as
`I = |P| / U`. That is a lower bound: the real current is `|P| / (U × PF)`, so with a
low power factor the real current is higher. For heavy resistive loads (PF ≈ 1, e.g.
instantaneous water heaters) it is accurate.

Turn on the switch **Ask meter for current** when you need exact current: the
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

### Option A: HACS (recommended)

1. In Home Assistant open **HACS**.
2. Top right **⋮ → Custom repositories**.
3. Repository: `https://github.com/marcvandam2/dtsu666-sniffer`, type **Integration**,
   click **Add**.
4. Search for **DTSU666 Sniffer** in HACS, open it and click **Download**.
5. Restart Home Assistant (**Settings → System → ⏻ → Restart Home Assistant**).

Updates show up in HACS like any other integration.

### Option B: manual

1. Download this repository (**Code → Download ZIP**) and unpack it.
2. Copy the folder `custom_components/dtsu666_sniffer` into the `custom_components`
   folder of your Home Assistant configuration, so you end up with
   `/config/custom_components/dtsu666_sniffer/manifest.json`.
   Use the *Samba share*, *Studio Code Server* or *Terminal & SSH* add-on, e.g. over SSH:

   ```bash
   cd /config
   mkdir -p custom_components
   wget -qO- https://github.com/marcvandam2/dtsu666-sniffer/archive/refs/heads/main.tar.gz \
     | tar xz --strip-components=2 -C custom_components dtsu666-sniffer-main/custom_components/dtsu666_sniffer
   ```

3. Restart Home Assistant.

### Add the integration

1. **Settings → Devices & services → + Add integration → DTSU666 Sniffer**.
2. Fill in the IP address of the RS485 gateway (port usually `502`), mode `sniff`,
   meter address `1`, and click **Submit**.
3. A device **DTSU666** appears with the sensors and the switch
   **Ask meter for current**. Power should update several times per second as soon as
   the Deye is running (with the inverter off there is no bus traffic to listen to).

Options can be changed later with **Configure** on the integration.

### Troubleshooting

* All sensors *unavailable*: check that the gateway is reachable on the TCP port, that
  the Deye is on (it is the one asking the meter), and the meter address.
* Only power and energy, no voltage: set *Voltage interval* above 0.
* Logs: **Settings → System → Logs**, filter on `dtsu666_sniffer`.

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
