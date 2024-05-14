# yar-cyber
An old-fashioned RL try

Some noob's notes for installation under Debian 20.04

sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev python3.9-minimal  
python3.9 -m venv yar-cyber
sudo apt install python3-pip python3-numpy libsdl2-dev libffi-dev
python -m pip install tcod

Commands (FR keyboard... only): 

        vi keys + yubn: movements
        TAB: auto-attack        ^a: disable auto-pickup
        f: target or fire       G: travel to
        r: reload               s: wait, hunker and take aim
        , or g : pickup         S (or ^s): save and quit
        d: drop                 ^p : previous message
        D: drop last item
        x: look
        >: descend
        <: ascend
        i: inventory
            [a-z]: use item
        o: auto-explore

Options :

    -h, --help            show this help message and exit
    -c, --curses          use curses rendering in terminal
    -s SEED, --seed SEED  fixed seed for static generation (new game only)
    -t PNG, --tiles PNG   path to a specific PNG tiles file (charmap CP437)
    -w, --wizard          start in wizard mode
    -i, --instant_travel  switch to instant travel with trails


Remarks :
Virtual envirnment :
https://docs.python.org/3/library/venv.html


Init tcod

https://python-tcod.readthedocs.io/en/latest/installation.html

sudo apt install python3-pip python3-numpy libsdl2-dev libffi-dev

Do not use : python3 -m pip install --user tcod ; ERROR: Can not perform a '--user' install. User site-packages are not visible in this virtualenv.

pip install tcod

python -m pip install tcod should work
