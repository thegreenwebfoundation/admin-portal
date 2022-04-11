# General
For whom is this documentation intended? x y and z so we will cover ... for a reason.

## Technologies used

|Technology   	|Version   	|
|---	|---	|
|       |       |

## Project structure

```App/
Controllers/
    User/
    Admin/

Models/
    User/
    Seller/

Views/
    User/
    Seller/
```

## Cheatsheets
The following list facilitates a usefull set of commands to execute basic operations in this virtual environment.<br> This list serves as a summary of all the commands discussed in the documentation and can be used as guide throughout.  

### General
|Command   	|Effect   	|
|---	|---	|
|```pipenv shell```   	| Enter virtual environment   	|
|```deactivate```   	| Leave virtual environment   	|

### Sphinx documentation
|Command   	|Effect   	|
|---	|---	|
|```sphinx-autobuild ./docs _build/```   	| Let Sphinx automatically build the project at every change in the documentation.<br> This operation can be stopped by interrupting the terminal by pressing ```Ctrl + c```    	|

### Tests
|Command   	|Effect   	|
|---	|---	|
|```make test```   	| Run the test makefile and summarize the results.     	|
