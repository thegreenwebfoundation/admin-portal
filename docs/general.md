# General 
```{admonition} Draft
For whom is this documentation intended? x y and z so we will cover ... for a reason.
```

## Technologies used

|Technology   	|Version   	|
|---	|---	|
|       |       |

## Project structure

```{admonition} Draft
The following structure is a placeholder. It can explain the structure of the project with some notable features.
```
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
The following list facilitates a useful set of commands to execute basic operations in this virtual environment. This list serves as a summary of all the commands discussed in the documentation and can be used as guide throughout.  

### Sphinx documentation
|Command   	|Effect   	|
|---	|---	|
|`make docs`   	| Build the documentation once.    	|
|`make docs.watch`  	| Build the documentation and keep automatically updating it until interrupted. This operation can be interrupted by pressing `Ctrl + c`  	|

### Testing
|Command   	|Effect   	|
|---	|---	|
|`make test`  	| Run the test makefile and summarize the results.     	|

### Miscellaneous
|Command   	|Effect   	|
|---	|---	| 
|`pipenv shell`   	| Enter virtual environment(in most cases not necessary as the terminal automatically enters the environment)   	|
|`deactivate`   	| Leave virtual environment   	|