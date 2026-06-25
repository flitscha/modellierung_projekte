# Airfoil Design and Analysis Tool

A tool for designing, exploring, analyzing, and optimizing airfoil geometries.

This project was developed as part of the university course **"PS Modellierung"**.

The objective of the project is to design an airfoil with **maximum mean lift** over an angle-of-attack (AoA) range from **0° to 10°**.

The final airfoil design is exported as a **Selig file** and used for **3D printing**.

---

## Team
- Noah Bichler
- Felix Campidell
- Aylin Postal

---

## Run Instructions

### Install dependencies

```bash
pip install numpy scipy dearpygui numba matplotlib
```

To use the XFoil comparison feature, you also need to install **XFoil** separately.

### Start the application

```bash
python main.py
```

---

## Features

### Design Explorer Tab

- Choose between multiple predefined design types (currently: NACA4, and Bezier-based designs)
- Each design type comes with its own parameter space
- Modify parameters using sliders
- Live preview of the generated airfoil geometry
- Live lift estimation using a panel solver
- Live pressure distribution visualisation
- Generate lift-vs-angle-of-attack plots
- Generate pressure distribution plots
- Export the airfoil in Selig format


### Optimisation Tab

- Optimize the parameter space, to maximize the mean lift
- Multiple optimization methods are available:
    - Differential Evolution
    - Nelder Mead
    - Powell


### XFoil Comparison Tab

- Compare the results from the implemented panel solver with XFoil simulations.

---

## AI Usage

AI tools were used during development.

It was especially useful for the GUI development.

All generated code and suggestions were carefully checked and adapted.

---

## References

The panel method solver was implemented following the description in:

- John D. Anderson, *Fundamentals of Aerodynamics* (Chapter 4.10).

The following open-source implementation served as a reference during development:

- [Panel Method – A Basic Application for Hand Drawn Airfoils](https://github.com/LaFleur93/Panel-Method-A-Basic-Application-for-Hand-Drawn-Airfoils)

