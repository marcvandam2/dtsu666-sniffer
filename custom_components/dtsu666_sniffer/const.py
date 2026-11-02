"""Constanten en registerkaart van de Chint DTSU666 (float32, big-endian)."""
DOMAIN = "dtsu666_sniffer"
CONF_MODE = "mode"
CONF_SLAVE = "slave"
CONF_INTERVAL = "interval"
CONF_U_INTERVAL = "u_interval"
# spanning per fase uit HA-sensoren van de Deye (wijzigt elke 5 min) voor stroom = |P| / U
CONF_U = ("u_entity_l1", "u_entity_l2", "u_entity_l3")
U_DEFAULT = tuple(f"sensor.deye_load_l{i}_voltage" for i in (1, 2, 3))
U_MAX_AGE = 900  # s; oudere of ontbrekende spanning -> 230 V
U_NOMINAAL = 230.0
MODE_SNIFF = "sniff"  # Waveshare-kanaal transparant: ruwe RTU-frames meelezen
MODE_POLL = "poll"    # Waveshare-kanaal Modbus TCP: zelf vragen

# register: (sleutel, naam, eenheid, factor, device_class, state_class)
REGS = {
    0x2000: ("u_ab", "Voltage L1-L2", "V", 0.1, "voltage", "measurement"),
    0x2002: ("u_bc", "Voltage L2-L3", "V", 0.1, "voltage", "measurement"),
    0x2004: ("u_ca", "Voltage L3-L1", "V", 0.1, "voltage", "measurement"),
    0x2006: ("u_a", "Voltage L1", "V", 0.1, "voltage", "measurement"),
    0x2008: ("u_b", "Voltage L2", "V", 0.1, "voltage", "measurement"),
    0x200A: ("u_c", "Voltage L3", "V", 0.1, "voltage", "measurement"),
    0x200C: ("i_a", "Current L1", "A", 0.001, "current", "measurement"),
    0x200E: ("i_b", "Current L2", "A", 0.001, "current", "measurement"),
    0x2010: ("i_c", "Current L3", "A", 0.001, "current", "measurement"),
    0x2012: ("p_t", "Power total", "W", 0.1, "power", "measurement"),
    0x2014: ("p_a", "Power L1", "W", 0.1, "power", "measurement"),
    0x2016: ("p_b", "Power L2", "W", 0.1, "power", "measurement"),
    0x2018: ("p_c", "Power L3", "W", 0.1, "power", "measurement"),
    0x201A: ("q_t", "Reactive power total", "var", 0.1, "reactive_power", "measurement"),
    0x202A: ("pf_t", "Power factor total", None, 0.001, "power_factor", "measurement"),
    0x202C: ("pf_a", "Power factor L1", None, 0.001, "power_factor", "measurement"),
    0x202E: ("pf_b", "Power factor L2", None, 0.001, "power_factor", "measurement"),
    0x2030: ("pf_c", "Power factor L3", None, 0.001, "power_factor", "measurement"),
    0x2044: ("freq", "Frequency", "Hz", 0.01, "frequency", "measurement"),
    0x101E: ("e_imp", "Energy import", "kWh", 1.0, "energy", "total_increasing"),
    0x1028: ("e_exp", "Energy export", "kWh", 1.0, "energy", "total_increasing"),
}
# schrijven naar HA: hooguit eens per MIN_WRITE_S, of meteen bij een sprong van JUMP
MIN_WRITE_S = 1.0
JUMP = {"current": 1.0, "power": 250.0}
# berekend uit de registers hierboven (stroom met teken: + import, - export)
EXTRA = [
    ("i_snel_a", "Current L1 (fast)", "A", 1.0, "current", "measurement"),
    ("i_snel_b", "Current L2 (fast)", "A", 1.0, "current", "measurement"),
    ("i_snel_c", "Current L3 (fast)", "A", 1.0, "current", "measurement"),
]
# vraag in de sniff-modus: Ua..Uc, Ia..Ic en Pt (14 registers; de Deye vraagt 6 en 12)
CURRENT_BLOCK = (0x2006, 14)
# spanningsvraag (standaard elke 60 s): Uca, Ua, Ub, Uc (8 registers, zie hierboven)
VOLTAGE_BLOCK = (0x2004, 8)
# blokken voor de poll-modus (start, aantal registers)
POLL_BLOCKS = [(0x2000, 0x34), (0x2044, 2), (0x101E, 12)]
