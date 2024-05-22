# COLOR_CODE = {
#     (255,255,255): 0,    # 0x00,
#     (0,0,0): 1,          # 0x01,
#     (170,0,0): 2,        # 0x02,
#     (0,170,0): 3,        # 0x03,
#     (170, 85, 0): 4,     # 0x04,
#     (0,0,170): 5,        # 0x05, 
#     (170,0,170): 6,      # 0x06,
#     (0,170,170): 7,      # 0x07,
#     (170,170,170): 8,    # 0x08, 
#     (85,85,85): 9,       # 0x09,
#     (255,85,85): 10,     # 0x0a,
#     (85,255,85): 11,     # 0x0b,
#     (255,255,85): 12,    # 0x0c,
#     (85,85,255): 13,     # 0x0d,
#     (255,85,255): 14,    # 0x0e,
#     (85,255,255): 15,    # 0x0f,  
#     (255,255,255): 16,   # 0x10,  
# }

COLOR_CODE = [
    (0,0,0),
    (170,0,0),
    (0,170,0),
    (170, 85, 0),
    (0,0,170), 
    (170,0,170),
    (0,170,170),
    (170,170,170), 
    (85,85,85),
    (255,85,85),
    (85,255,85),
    (255,255,85),
    (85,85,255),
    (255,85,255),
    (85,255,255),  
    (255,255,255),  
]

# Same loop in Main
COLOR_PAIR= {}
i=0
for bg in range(0,16):
    for fg in range(0,16):
        i+=1
        COLOR_PAIR[(COLOR_CODE[fg]+COLOR_CODE[bg])] = i

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

_colorToANSI = {
    (0,0,0):"30",
    (170,0,0):"31",
    (0,170,0):"32",
    (170, 85, 0):"33",
    (0,0,170):"34", 
    (170,0,170):"35",
    (0,170,170):"36",
    (170,170,170):"37", 
    (85,85,85):"30;1",
    (255,85,85):"31;1",
    (85,255,85):"32;1",
    (255,255,85):"33;1",
    (85,85,255):"34;1",
    (255,85,255):"35;1",
    (85,255,255):"36;1",
    (255,255,255):"37;1",
}

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
ascend = (0x9F, 0x3F, 0xFF)

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

