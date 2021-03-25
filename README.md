# Learning from Sparse Demonstrations

This project is the implementation of the paper _**Learning from Sparse Demonstrations**_, co-authored by
Wanxin Jin, Todd D. Murphey, Dana Kulić, Neta Ezer, Shaoshuai Mou. Please find more details in

* Paper: https://arxiv.org/abs/2008.02159 for technical details.
* Demos: https://wanxinjin.github.io/posts/lfsd for video demos.

This repo has been tested with:
* Ubuntu 20.04.2 LTS, Python 3.8.5, CasADi 3.5.5, Numpy 1.20.1, IPOPT(coinor-libipopt-dev) 3.11.9-2.2build2.
* macOS 11.2.3, Python 3.9.2, CasADi 3.5.5, Numpy 1.20.1, IPOPT 3.13.4.

## Project Structure
The current version of the project consists of three folders:

* **_CPDP_**: a package including an optimal control solver, functionalities for differentiating maximum principle, and functionalities to solve the differential maximum principle.  
* **_JinEnv_**: an independent package providing various robot environments to simulate on.
* **_Examples_**: various examples to reproduce the experiments in the paper.
* **_lib_**: various helper libraries for obtaining human demonstrations via GUI.
* **_test_**: various test files for testing GUI.


## Dependency Packages
Please make sure that the following packages have already been installed before you use the codes.
* [CasADi](https://web.casadi.org/): version > 3.5.1.
* [IPOPT](https://coin-or.github.io/Ipopt/): need this for solving NLP in CasADi, the binary installation is fine.
* [Numpy](https://numpy.org/): version > 1.18.1.
* [Transforms3d](https://pypi.org/project/transforms3d/)
* [Scipy](https://www.scipy.org/)
* [matplotlib](https://matplotlib.org/)
* [FFmpeg](https://ffmpeg.org/): need this for saving the data visualization.
* [PyQt5](https://pypi.org/project/PyQt5/)

You can run [`test_casadi_ipopt.py`](test_casadi_ipopt.py) to test if [IPOPT](https://coin-or.github.io/Ipopt/) works correctly with [CasADi](https://web.casadi.org/).


## Installation

* For Linux:
```
$ sudo apt update
$ sudo apt install build-essential coinor-libipopt-dev ffmpeg libxcb-xinerama0
$ pip3 install casadi numpy transforms3d scipy matplotlib pyqt5
$ git clone https://github.com/zehuilu/Learning-from-Sparse-Demonstrations
$ cd <ROOT_DIRECTORY>
$ mkdir trajectories data
$ python3 test_casadi_ipopt.py # test ipopt
```


* For macOS:
```
$ brew update
$ brew install libxcb ffmpeg
$ pip3 install casadi numpy transforms3d scipy matplotlib pyqt5
```

To make [IPOPT](https://coin-or.github.io/Ipopt/) work with macOS default compiler [Clang](https://clang.llvm.org/), we need [GFortran](https://gcc.gnu.org/wiki/GFortran), which comes with [GCC](https://gcc.gnu.org/). More details see [here](https://projects.coin-or.org/BuildTools/wiki/current-issues).
```
$ brew update
$ brew install gcc ipopt libomp
```

Sometimes [CasADi](https://web.casadi.org/) can't find [GFortran](https://gcc.gnu.org/wiki/GFortran), and returns an error `Cannot load shared library 'libcasadi_nlpsol_ipopt.so'` due to `"Library not loaded: @rpath/libgfortran.4.dylib"`. In this case, you need to manually create a symlink for `libgfortran.4.dylib`. An example is shown below:

First, search a specific directory to make sure you do have `libgfortran.X.dylib` (`X` is your `libgfortran`'s version):
```
$ grep -l 'libgfortran' /usr/local/Cellar/gcc/<GCC_VERSION>/lib/gcc/<GCC_VERSION_FIRST_SECTION>/**
$ # example: grep -l 'libgfortran' /usr/local/Cellar/gcc/10.2.0_4/lib/gcc/10/**
```
If you see some files includes `libgfortran.X.dylib`, for example:
```
grep: /usr/local/Cellar/gcc/10.2.0_4/lib/gcc/10/gcc: Is a directory
/usr/local/Cellar/gcc/10.2.0_4/lib/gcc/10/libgfortran.5.dylib
/usr/local/Cellar/gcc/10.2.0_4/lib/gcc/10/libgfortran.a
/usr/local/Cellar/gcc/10.2.0_4/lib/gcc/10/libgfortran.dylib
```

Then continue with the following instructions. If not, try to install [GCC](https://gcc.gnu.org/) first.

Let's say you have `libgfortran.5.dylib` (or generally `libgfortran.X.dylib`) but [CasADi](https://web.casadi.org/) cannot load `libgfortran.4.dylib`, then you need to create a symlink in a specific directory `/usr/local/lib/`, which links to `libgfortran.X.dylib`. (The backward compatibility should be fine.)
```
$ ln /usr/local/Cellar/gcc/<GCC_VERSION>/lib/gcc/<GCC_VERSION_FIRST_SECTION>/libgfortran.X.dylib /usr/local/lib/libgfortran.4.dylib
$ # example: ln /usr/local/Cellar/gcc/10.2.0_4/lib/gcc/10/libgfortran.5.dylib /usr/local/lib/libgfortran.4.dylib
```

Finally, run [`test_casadi_ipopt.py`](test_casadi_ipopt.py) to test if [IPOPT](https://coin-or.github.io/Ipopt/) works correctly with [CasADi](https://web.casadi.org/).
```
$ git clone https://github.com/zehuilu/Learning-from-Sparse-Demonstrations
$ cd <ROOT_DIRECTORY>
$ mkdir trajectories data
$ python3 test_casadi_ipopt.py # test ipopt
```

Feel free to start an issue if you have any questions or post your questions/thoughts in our Discussions channel. We're happy to help!


## How to Train Your Robots.
Below is the procedure of how to apply the codes to train your robot to learn from sparse demonstrations.

* **Step 1.** Load a robot environment from JinEnv library (specify parameters of the robot dynamics).
* **Step 2.** Specify a parametric time-warping function and a parametric  cost function (loaded from JinEnv).
* **Step 3.** Provide some sparse demonstrations and define the trajectory loss function.
* **Step 4.** Set the learning rate and start training your robot (apply CPDP) given initial guesses.
* **Step 5.** Done, check and simulate your robot visually (use animation utilities from JinEnv).

The quickest way to hand on the codes is to check and run the examples under the folder [`Examples/`](Examples/) .

There are some parameters for the quadrotor demo, including the 3D space limit and the average speed for estimating the time waypoints.

Run the algorithm with pre-defined waypoints:
```
$ cd <ROOT_DIRECTORY>
$ python3 Examples/quad_example.py
```

Run the algorithm with human inputs:
```
$ cd <ROOT_DIRECTORY>
$ python3 Examples/quad_example_human_input.py
```

To obtain human input via matplotlib ginput():
```
$ cd <ROOT_DIRECTORY>
$ python3 test/test_input.py
```

To obtain human input via a GUI with PyQt5:
```
$ cd <ROOT_DIRECTORY>
$ python3 test/test_gui.py
```


## Contact Information and Citation
If you have encountered a bug in your implementation of the code, please feel free to let me known via email:

* Name: wanxin jin (he/his)
* Email: wanxinjin@gmail.com

The codes are under regularly update.

If you find this project helpful in your publications, please consider citing our paper.
``` 
@article{jin2020learning,
    title={Learning from Sparse Demonstrations},
    author={Jin, Wanxin and Murphey, Todd D and Kuli{\'c}, Dana and Ezer, Neta and Mou, Shaoshuai},
    journal={arXiv preprint arXiv:2008.02159},
    year={2020}
}
```