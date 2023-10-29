COLOR_PAIR = {
    (255,255,255): 0,
    (0,0,0): 1,
    (170,0,0): 2,
    (0,170,0): 3,
    (170, 85, 0): 4,
    (0,0,170): 5, 
    (170,0,170): 6,
    (0,170,170): 7,
    (170,170,170): 8, 
    (85,85,85): 9,
    (255,85,85): 10,
    (85,255,85): 11,
    (255,255,85): 12,
    (85,85,255): 13,
    (255,85,255): 14,
    (85,255,255): 15,  
}


# Normal Linux Console palette
c1 = n_black = (0,0,0)
c2 = n_red = (170,0,0)
c3 = n_green = (0,170,0)
c4 = n_brown = (170,85,0)
c5 = n_blue = (0,0,170)
c6 = n_purple = (170,0,170)
c7 = n_cyan = (0,170,170)
c8 = n_gray = (170,170,170)
# Bright
c9 = b_darkgray = (85,85,85)
c10 = b_orange = (255,85,85)
c11 = b_green = (85,255,85)
c12 = b_yellow = (255,255,85)
c13 = b_blue = (85,85,255)
c14 = b_pink = (255,85,255)
c15 = b_cyan = (85,255,255)
c0 = b_white = (255,255,255)

#x3F = 63
#x55 = 85
#xA0 = 160
#xAA = 170
#xC0 = 192

white = b_white
black = n_black
red = n_red
gray = b_darkgray

player_atk = n_gray
enemy_atk = b_orange
needs_target = b_cyan
status_effect_applied = b_green
descend = (0x9F, 0x3F, 0xFF)

player_die = n_red
enemy_die = n_red

invalid = b_darkgray
debug = b_yellow
impossible = n_gray
error = n_red

welcome_text = n_cyan
health_recovered = n_green

bar_text = b_white

menu_title = b_yellow
menu_text = b_white

