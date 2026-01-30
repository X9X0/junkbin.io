import { Download, FileSpreadsheet } from 'lucide-react';

const BOM_TEMPLATE_CSV = `Reference Designator,Part Number,Manufacturer,Component Type,Package,Quantity,Location,Notes
U1,LM7805,Texas Instruments,regulator,TO-220,1,Near power input,5V linear regulator
U2,STM32F103C8T6,STMicroelectronics,mcu,LQFP-48,1,Center of board,Main microcontroller
R1,10K,Generic,resistor,0805,1,Near U2 pin 1,Pull-up resistor
R2,10K,Generic,resistor,0805,1,Near U2 pin 2,Pull-up resistor
C1,100uF,Nichicon,capacitor,Radial 8x12,1,Near power input,Bulk decoupling
C2,100nF,Generic,capacitor,0805,4,Near each IC,Bypass capacitors
D1,1N4007,Generic,diode,DO-41,1,Power input,Reverse polarity protection
LED1,Red LED,Generic,led,0805,1,Front panel,Power indicator`;

const BOM_TEMPLATE_INSTRUCTIONS = `# Junkbin.io BOM Template Instructions

## Column Descriptions

- **Reference Designator**: The component label on the PCB (e.g., U1, R5, C12)
- **Part Number**: Manufacturer's part number
- **Manufacturer**: Component manufacturer name
- **Component Type**: One of: ic, mcu, transistor, mosfet, diode, regulator, opamp, resistor, capacitor, inductor, transformer, crystal, relay, switch, connector, led, display, sensor, module, other
- **Package**: Physical package type (e.g., SOT-23, SOIC-8, 0805, QFP-48)
- **Quantity**: Number of this component on the board
- **Location**: Description of where the component is located
- **Notes**: Any additional information

## Tips

1. Use the exact part number from the component marking when possible
2. Reference designators help others locate components on the board
3. Include datasheet URLs in notes when available
4. For generic components (resistors, capacitors), include the value in part number or notes

## Supported Component Types

Active: ic, mcu, transistor, mosfet, diode, regulator, opamp
Passive: resistor, capacitor, inductor, transformer, crystal, fuse, ferrite
Electromechanical: relay, switch, connector, socket
RF/Wireless: antenna, rf_module, balun
Power: battery, power_jack, usb_port
Display/Output: led, display, speaker
Sensors: sensor, thermistor
Modules: module, pcb_assembly
Cabling: cable, flex_cable, coax
Other: heatsink, shield, mechanical, other
`;

export default function BomTemplateDownload() {
  const downloadCsv = () => {
    const blob = new Blob([BOM_TEMPLATE_CSV], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'junkbin-bom-template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadInstructions = () => {
    const blob = new Blob([BOM_TEMPLATE_INSTRUCTIONS], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'junkbin-bom-instructions.md';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card-cyber p-4">
      <h3 className="font-mono text-sm text-cyber-green mb-3 flex items-center gap-2">
        <FileSpreadsheet className="h-4 w-4" />
        BOM TEMPLATES
      </h3>
      <p className="text-xs text-gray-500 mb-4">
        Download templates to document components in a standardized format.
      </p>
      <div className="flex flex-wrap gap-3">
        <button
          onClick={downloadCsv}
          className="flex items-center gap-2 text-xs font-mono text-cyber-green hover:text-white border border-cyber-green/50 hover:border-cyber-green px-3 py-2 transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          CSV Template
        </button>
        <button
          onClick={downloadInstructions}
          className="flex items-center gap-2 text-xs font-mono text-gray-400 hover:text-white border border-cyber-light/50 hover:border-cyber-light px-3 py-2 transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          Instructions
        </button>
      </div>
    </div>
  );
}
