# Automate data processing and benchmarking of algorithms

XAutomate class runs an application (program, script, etc) using parametrized input.
The results of each computation (data, tables, images) are saved in the folder with a structured name.
Name is derived from the corresponding parameters and can be structured using TreeOrderer class.

The target application should support parametrization via:
- command line
- setting file

Target application can output results, which might be then collected by XAnalyzer class.
