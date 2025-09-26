# Mechanism compilation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This directory provides the workflow to compile sub-modules into CHEMKIN and Cantera YAML format.

## How to use

1. **Select sub-modules**  
 Open and edit `submodules.yaml` to specify the sub-modules you want to include in the final mechanism.

2. **Compile the mechanism**  
 Run the following command in the terminal:

 ```sh
 ./compile_c3mech.py
 ```

The command writes `.CKI,` `.THERM,` and `.TRAN` files to the `output/` directory. For more information, use:

```sh
./compile_c3mech.py -h
```

## Installing dependencies

You can install the dependencies, for example, with:

```sh
pip3 install pyyaml cantera --user
```

The dependency on Cantera is optional.

## Notes and recommendations

- **Selecting necessary sub-modules:** Selecting only the necessary sub-modules facilitates and speeds up kinetic simulations. 
- **User responsibility:** The user must select an appropriate sub-modules for a simulation case. 

If you have further questions or need additional help, please feel free to open an issue or [contact us](r.langer@itv.rwth-aachen.de).
