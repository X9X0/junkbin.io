// Kept in sync with COMPONENT_TYPES in backend/config/settings/base.py
export interface ComponentTypeOption {
  value: string;
  label: string;
}

export const COMPONENT_TYPES: ComponentTypeOption[] = [
  { value: '', label: 'All Types' },
  // Active
  { value: 'ic', label: 'Integrated Circuit' },
  { value: 'mcu', label: 'Microcontroller' },
  { value: 'transistor', label: 'Transistor' },
  { value: 'mosfet', label: 'MOSFET' },
  { value: 'diode', label: 'Diode' },
  { value: 'regulator', label: 'Voltage Regulator' },
  { value: 'opamp', label: 'Op-Amp' },
  // Passive
  { value: 'resistor', label: 'Resistor' },
  { value: 'capacitor', label: 'Capacitor' },
  { value: 'inductor', label: 'Inductor' },
  { value: 'transformer', label: 'Transformer' },
  { value: 'crystal', label: 'Crystal/Oscillator' },
  { value: 'fuse', label: 'Fuse' },
  { value: 'ferrite', label: 'Ferrite Bead' },
  // Electromechanical
  { value: 'relay', label: 'Relay' },
  { value: 'switch', label: 'Switch' },
  { value: 'connector', label: 'Connector' },
  { value: 'socket', label: 'Socket/Header' },
  // RF/Wireless
  { value: 'antenna', label: 'Antenna' },
  { value: 'rf_module', label: 'RF Module' },
  { value: 'balun', label: 'Balun/Filter' },
  // Power
  { value: 'battery', label: 'Battery/Cell' },
  { value: 'power_jack', label: 'Power Jack' },
  { value: 'usb_port', label: 'USB Port' },
  // Display/Output
  { value: 'led', label: 'LED' },
  { value: 'display', label: 'Display/LCD' },
  { value: 'speaker', label: 'Speaker/Buzzer' },
  // Sensors
  { value: 'sensor', label: 'Sensor' },
  { value: 'thermistor', label: 'Thermistor/NTC' },
  // Modules
  { value: 'module', label: 'Module/Daughter Board' },
  { value: 'pcb_assembly', label: 'PCB Assembly' },
  // Cabling
  { value: 'cable', label: 'Cable/Wire Harness' },
  { value: 'flex_cable', label: 'Flex Cable/FPC' },
  { value: 'coax', label: 'Coaxial Cable' },
  // Other
  { value: 'heatsink', label: 'Heatsink' },
  { value: 'shield', label: 'EMI Shield' },
  { value: 'mechanical', label: 'Mechanical Part' },
  { value: 'other', label: 'Other' },
];
