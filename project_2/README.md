# Bridge Design and Analysis Tool.

A tool for designing, exploring, analyzing, and optimizing lightweight bridge cross sections for 3D printing.

The project was developed as part of the course "PS Modellierung".

The goal is to design a bridge cross section with minimal weight while satisfying some constraints.

---

## Project Goal

Design a bridge with:

- Span: 300 mm
- Maximum height: 15 mm
- Load: 5 kg applied in the center
- Maximum allowed deflection: 3 mm

The bridge design should be submitted as an SVG file so that it can be 3D printed with PLA.

---

## Team
- Noah Bichler
- Felix Campidell
- Aylin Postal

---

## Run Instructions

### Install dependencies

```bash
pip install numpy scipy dearpygui
```

### Start the application

```bash
python main.py
```

---

## Features

### Design Explorer Tab

- Choose between multiple predefined bridge/truss types
- Each bridge type comes with its own parameter space
- Modify parameters using sliders
- Live preview of the generated bridge geometry
- Live deflection estimation using a truss solver
- Weight estimation
- Export bridges as SVG


### Analysis Tab

- More detailed analysis of a bridge, using FEM solver
- Stress visualization


### Optimisation Tab

- Grid search in the parameter space
- Attempts to minimize weight while satisfying deflection constraints

---

## AI Usage

AI tools were used during development.

It was especially useful for the GUI development.

All generated code and suggestions were carefully checked and adapted.

