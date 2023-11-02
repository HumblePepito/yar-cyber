# yar-cyber
An old-fashioned RL try

Some noob's notes for installation under Debian 20.04

Virtual envirnment :
https://docs.python.org/3/library/venv.html

sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev python3.9-minimal  

python3.9 -m venv yar-cyber

Init tcod
https://python-tcod.readthedocs.io/en/latest/installation.html

sudo apt install python3-pip python3-numpy libsdl2-dev libffi-dev

Do not use : python3 -m pip install --user tcod ; ERROR: Can not perform a '--user' install. User site-packages are not visible in this virtualenv.

pip install tcod
python -m pip install tcod should work
