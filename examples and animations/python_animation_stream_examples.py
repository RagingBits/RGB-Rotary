import serial
import time
import math
import random

PORT = "COM4"
BAUD = 115200
NUM_LEDS = 32
BREATH_PERIOD = 2
TRAIL_DECAY = 0.03
INDICATOR_BRIGHTNESS = 1.0

# =======================
# GENERIC ENGINE RESOURCES
# =======================
class AnimationState:
    def __init__(self, num_leds):
        self.num_leds = num_leds
        # LED buffer: list of [r,g,b] tuples
        self.led_buffer = [(0, 0, 0)] * num_leds
        
        # Trail buffer for trail effects
        self.trail_buffer = [0.0] * num_leds
        
        # Flame buffers
        self.flame_current = [(0,0,0)] * num_leds
        self.flame_target = [(0,0,0)] * num_leds
        self.flame_frame_count = 0
        
        # Wave offsets
        self.wave_offset = 0
        self.rainbow_offset = 0
        
        # Misc variables
        self.breath = 0.0
        self.time_start = time.time()
        
        # User-accessible generic variables
        self.vars = {}
        
        # Inputs
        self.button_pressed = False
        self.indicator_pos = 0

# =======================
# GENERIC ANIMATIONS
# =======================
def heartbeat_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    t = time.time() - s.time_start
    # Double-beat approximation
    beat_speed = 1.0 if not s.button_pressed else 2.0
    # Create "boom-boom" effect using two sine peaks
    intensity_factor = (math.sin(2*math.pi*beat_speed*t)**2 +
                        0.5 * math.sin(2*math.pi*beat_speed*2*t)**2)
    brightness = int((50 + 205 * intensity_factor) * intensity)
    
    if(brightness>255):
        brightness = 255
    
    for i in range(num_leds):
        r, g, b = brightness, 0, 0
        if i == s.indicator_pos % num_leds:
            r, g, b = 255, 255, 255
        data += bytes((g, r, b))
    return data

def fire_flicker_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    s.flame_frame_count += 1
    if s.flame_frame_count >= 20:
        for i in range(num_leds):
            base_r = random.randint(70, 126)
            base_g = random.randint(5, 20)
            base_b = 0
            if s.button_pressed:
                base_r = min(255, base_r * 2)
            s.flame_target[i] = (base_r, base_g, base_b)
        s.flame_frame_count = 0
    for i in range(num_leds):
        cur_r, cur_g, cur_b = s.flame_current[i]
        tgt_r, tgt_g, tgt_b = s.flame_target[i]
        new_r = int(cur_r + (tgt_r - cur_r) * 0.1)
        new_g = int(cur_g + (tgt_g - cur_g) * 0.1)
        new_b = int(cur_b + (tgt_b - cur_b) * 0.1)
        s.flame_current[i] = (new_r, new_g, new_b)
        r, g, b = (255,255,255) if i == s.indicator_pos % num_leds else (new_r, new_g, new_b)
        r = int(r*intensity)
        g = int(g*intensity)
        b = int(b*intensity)
        data += bytes((g, r, b))
    return data

def sine_motion_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    WAVE_AMPLITUDE = 200
    WAVE_BASE = 55
    speed = 0.3
    for i in range(num_leds):
        phase = 2 * math.pi * (i + s.wave_offset) / num_leds
        brightness = int(WAVE_BASE + WAVE_AMPLITUDE * math.sin(phase))
        brightness = max(0, min(255, brightness))
        r, g, b = (0,0,brightness)
        if i == s.indicator_pos % num_leds:
            r, g, b = 255,255,255
        r = int(r*intensity)
        g = int(g*intensity)
        b = int(b*intensity)
        data += bytes((g,r,b))
    increment = speed if not s.button_pressed else -speed
    s.wave_offset = (s.wave_offset + increment) % num_leds
    return data

def mood_gradient_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    color1, color2 = ((0,0,255),(75,0,130)) if s.button_pressed else ((255,100,0),(255,0,50))
    for i in range(num_leds):
        t = ((i + s.wave_offset) % num_leds)/(num_leds-1)
        r = int((color1[0]*(1-t) + color2[0]*t)*intensity)
        g = int((color1[1]*(1-t) + color2[1]*t)*intensity)
        b = int((color1[2]*(1-t) + color2[2]*t)*intensity)
        if i == s.indicator_pos % num_leds:
            r, g, b = int(255*intensity), int(255*intensity), int(255*intensity)
        data += bytes((g,r,b))
    s.wave_offset = (s.wave_offset+1)%num_leds
    return data

def wheel(pos):
    if pos < 85:
        return (pos*3, 255-pos*3, 0)
    elif pos < 170:
        pos -= 85
        return (255-pos*3, 0, pos*3)
    else:
        pos -= 170
        return (0, pos*3, 255-pos*3)

def chasing_rainbow_with_indicator_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    for i in range(num_leds):
        color_index = (i*256//num_leds + s.rainbow_offset)%256
        r,g,b = wheel(color_index)
        if i == s.indicator_pos % num_leds:
            r,g,b = int(255*intensity), int(255*intensity), int(255*intensity)
        else:
            r = int(r*intensity)
            g = int(g*intensity)
            b = int(b*intensity)
        data += bytes((g,r,b))
    s.rainbow_offset = (s.rainbow_offset - 2 if s.button_pressed else s.rainbow_offset + 2) % 256
    return data

def wave_sine_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    WAVE_BASE = 55
    WAVE_AMPLITUDE = 200
    for i in range(num_leds):
        phase = (i+s.wave_offset)*2*math.pi/num_leds
        brightness = int(WAVE_BASE + WAVE_AMPLITUDE*math.sin(phase))
        brightness = max(0, min(255, brightness))
        r, g, b = (0,0,brightness)
        if i == s.indicator_pos % num_leds:
            r,g,b = int(255*intensity), int(255*intensity), int(255*intensity)
        else:
            r = int(r*intensity)
            g = int(g*intensity)
            b = int(b*intensity)
        data += bytes((g,r,b))
    s.wave_offset += -1 if s.button_pressed else 1
    s.wave_offset %= num_leds
    return data

def pyramid_indicator_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    s.breath = (math.sin(time.time()*2*math.pi/BREATH_PERIOD)+1)/2
    s.breath = 0.3 + 0.7*s.breath
    pos = s.indicator_pos % num_leds
    PYRAMID_SIZE = 1
    for i in range(num_leds):
        if s.button_pressed:
            r,g,b = 0,0,30
        else:
            r,g,b = 30,0,0
        dist = min(abs(i-pos), num_leds-abs(i-pos))
        if dist <= PYRAMID_SIZE:
            scale = (PYRAMID_SIZE-dist+1)/(PYRAMID_SIZE+1)
            if s.button_pressed:
                b = int((255*s.breath)*scale + b*(1-scale))
                g = int((50*s.breath)*scale + g*(1-scale))
                r = int((50*s.breath)*scale + r*(1-scale))
            else:
                r = int((255*s.breath)*scale + r*(1-scale))
                g = int((50*s.breath)*scale + g*(1-scale))
                b = 0
        data += bytes((g,r,b))
    return data

def trail_indicator_frame(s: AnimationState, num_leds, intensity=1.0):
    data = bytearray()
    # update trail
    for i in range(num_leds):
        s.trail_buffer[i] = max(0.0, s.trail_buffer[i]-TRAIL_DECAY)
    pos = s.indicator_pos % num_leds
    s.trail_buffer[pos] = INDICATOR_BRIGHTNESS
    s.breath = (math.sin(time.time()*2*math.pi/BREATH_PERIOD)+1)/2
    s.breath = 0.3 + 0.7*s.breath
    for i in range(num_leds):
        intensity_val = s.trail_buffer[i]
        if s.button_pressed:
            r = int(0*intensity_val*intensity)
            g = int(30*intensity_val*intensity)
            b = int(255*intensity_val*intensity)
        else:
            r = int(255*intensity_val*intensity)
            g = int(30*intensity_val*intensity)
            b = int(0*intensity_val*intensity)
        if i == pos:
            if s.button_pressed:
                r = int(0*s.breath*intensity)
                g = int(100*s.breath*intensity)
                b = int(255*s.breath*intensity)
            else:
                r = int(255*s.breath*intensity)
                g = int(100*s.breath*intensity)
                b = int(0*s.breath*intensity)
        data += bytes((g,r,b))
    return data
    
    
def trail_indicator_frame(s: AnimationState, num_leds, intens=1.0):
    """Single LED yellow indicator with red trail fading over time"""
    
    BREATH_PERIOD = 2       # frames per full breath
    TRAIL_DECAY = 0.03       # amount the trail fades per frame
    data = bytearray()

    # --- Step 1: Update trail ---
    for i in range(num_leds):
        s.trail_buffer[i] = max(0.0, s.trail_buffer[i] - TRAIL_DECAY)

    # Add indicator to trail
    pos = s.indicator_pos % num_leds
    s.trail_buffer[pos] = intens

    # --- Step 2: Breathing effect for indicator (yellow→orange) ---
    # Use time.time() for continuous breathing
    s.breath = (math.sin(time.time() * 2 * math.pi / BREATH_PERIOD) + 1) / 2
    s.breath = 0.3 + 0.7 * s.breath  # scale to 0.5..1.0 for visibility
    
    
    # --- Step 3: Build LED frame ---
    for i in range(num_leds):
        intensity = s.trail_buffer[i]*intens

        # Trail: light red → red
        if(s.button_pressed == True):
            r = int(0 * intensity)
            g = int(30 * intensity)
            b = int(255 * intensity)
        else:
            r = int(255 * intensity)
            g = int(30 * intensity)
            b = int(0 * intensity)

        # Indicator overlay: yellow → orange
        if i == pos:  
            if(s.button_pressed == True):
                r = int(0* s.breath)
                g = int(100 * s.breath)
                b = int(255 * s.breath)
            else:
                r = int(255* s.breath)
                g = int(100 * s.breath)
                b = int(0 * s.breath)

        data += bytes((g, r, b))  # GRB order

    return data
    
# =======================
# RUNNER
# =======================
def run_animation(frame_builder, intensity=1.0):
    s = AnimationState(NUM_LEDS)
    with serial.Serial(PORT, BAUD, timeout=0.01) as ser:
        # initial frame
        current_frame = frame_builder(s, NUM_LEDS, intensity)
        ser.write(b'F'+current_frame)

        while True:
            current_frame = frame_builder(s, NUM_LEDS, intensity)
            ch = ser.read(1)
            if ch:
                if ch == b')':
                    s.indicator_pos += 1
                elif ch == b'(':
                    s.indicator_pos -= 1
                elif ch == b'p':
                    s.button_pressed = True
                elif ch == b'P':
                    s.button_pressed = False
                elif ch == b'A':
                    ser.write(b'F'+current_frame)
            time.sleep(0.001)

# =======================
# MAIN
# =======================
if __name__ == "__main__":
    try:
        # Change this to any animation
        run_animation(trail_indicator_frame, intensity=0.99)
    except KeyboardInterrupt:
        print("\nExiting.")
