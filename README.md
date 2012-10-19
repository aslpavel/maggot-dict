Maggot Dictionary
=================
It's a pure python (for now console based) dictionary

Dictionary Formats
------------------
* DICT   (.dict|.idx)
* Lingvo (.dsl)


Features
--------
* Bash completion
* Colored output
* Compatible with python 3
* Fast | Lightweight | Extensible


Dependencies
------------
Python >= 2.7


Installation
------------
From archive:
```
# make install   # installation
# make uninstall # removal
```

From git:
```
$ git clone git://github.com/aslpavel/maggot-dict.git maggot-dict
$ cd maggot-dict
$ git submodule update --init --recursive
# make install   # installation
# make uninstall # removal
```

For Arch Linux users:
```
# yaourt -S maggot-dict-git
```

Usage:
-----
```
Usage: maggot-dict-cli [options] <word>
options:
    -I <file> : install dictionary
    -U <name> : uninstall dictionary
    -d <name> : disable dictionary
    -s        : show statistics
    -h|?      : show this help message
```

Completion and word:

![show word](https://raw.github.com/aslpavel/maggot-dict/master/screenshots/word.png "show word")

Statistics:

![show statistics](https://raw.github.com/aslpavel/maggot-dict/master/screenshots/stat.png "show statistics")

Installation:

![install dictionary](https://raw.github.com/aslpavel/maggot-dict/master/screenshots/install.png "install dictionary")
