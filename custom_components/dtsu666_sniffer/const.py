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
    0x2000: ("u_ab", "Spanning L1-L2", "V", 0.1, "voltage", "measurement"),
    0x2002: ("u_bc", "Spanning L2-L3", "V", 0.1, "voltage", "measurement"),
    0x2004: ("u_ca", "Spanning L3-L1", "V", 0.1, "voltage", "measurement"),
    0x2006: ("u_a", "Spanning L1", "V", 0.1, "voltage", "measurement"),
    0x2008: ("u_b", "Spanning L2", "V", 0.1, "voltage", "measurement"),
    0x200A: ("u_c", "Spanning L3", "V", 0.1, "voltage", "measurement"),
    0x200C: ("i_a", "Stroom L1", "A", 0.001, "current", "measurement"),
    0x200E: ("i_b", "Stroom L2", "A", 0.001, "current", "measurement"),
    0x2010: ("i_c", "Stroom L3", "A", 0.001, "current", "measurement"),
    0x2012: ("p_t", "Vermogen totaal", "W", 0.1, "power", "measurement"),
    0x2014: ("p_a", "Vermogen L1", "W", 0.1, "power", "measurement"),
    0x2016: ("p_b", "Vermogen L2", "W", 0.1, "power", "measurement"),
    0x2018: ("p_c", "Vermogen L3", "W", 0.1, "power", "measurement"),
    0x201A: ("q_t", "Blindvermogen totaal", "var", 0.1, "reactive_power", "measurement"),
    0x202A: ("pf_t", "Arbeidsfactor totaal", None, 0.001, "power_factor", "measurement"),
    0x202C: ("pf_a", "Arbeidsfactor L1", None, 0.001, "power_factor", "measurement"),
    0x202E: ("pf_b", "Arbeidsfactor L2", None, 0.001, "power_factor", "measurement"),
    0x2030: ("pf_c", "Arbeidsfactor L3", None, 0.001, "power_factor", "measurement"),
    0x2044: ("freq", "Frequentie", "Hz", 0.01, "frequency", "measurement"),
    0x101E: ("e_imp", "Energie import", "kWh", 1.0, "energy", "total_increasing"),
    0x1028: ("e_exp", "Energie export", "kWh", 1.0, "energy", "total_increasing"),
}
# berekend uit de registers hierboven
EXTRA = [
    ("i_snel_a", "Stroom L1 (snel)", "A", 1.0, "current", "measurement"),
    ("i_snel_b", "Stroom L2 (snel)", "A", 1.0, "current", "measurement"),
    ("i_snel_c", "Stroom L3 (snel)", "A", 1.0, "current", "measurement"),
    ("i_max", "Stroom hoogste fase", "A", 1.0, "current", "measurement"),
]
# vraag in de sniff-modus: Ua..Uc, Ia..Ic en Pt (14 registers; de Deye vraagt 6 en 12)
CURRENT_BLOCK = (0x2006, 14)
# spanningsvraag (standaard elke 60 s): Uca, Ua, Ub, Uc (8 registers, zie hierboven)
VOLTAGE_BLOCK = (0x2004, 8)
# blokken voor de poll-modus (start, aantal registers)
POLL_BLOCKS = [(0x2000, 0x34), (0x2044, 2), (0x101E, 12)]
