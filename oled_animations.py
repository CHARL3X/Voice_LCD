"""
OLED Animation System - Tech/Cyberpunk Aesthetic
Provides animation primitives and visual effects for tiny OLED displays
"""
import time
import math
from PIL import ImageDraw, ImageFont

class AnimationState:
    """Track animation state and timing"""
    def __init__(self):
        self.start_time = time.time()
        self.progress = 0.0  # 0.0 to 1.0

    def update(self, duration=1.0):
        """Update animation progress (0.0 to 1.0)"""
        elapsed = time.time() - self.start_time
        self.progress = min(elapsed / duration, 1.0)
        return self.progress

    def is_complete(self):
        """Check if animation finished"""
        return self.progress >= 1.0

    def reset(self):
        """Reset animation"""
        self.start_time = time.time()
        self.progress = 0.0


class TechDrawing:
    """Tech/Cyberpunk themed drawing primitives"""

    @staticmethod
    def draw_corner_brackets(draw, width, height, size=4):
        """Draw corner brackets [  ] framing the display"""
        # Top-left
        draw.line([(0, 0), (size, 0)], fill="white", width=1)
        draw.line([(0, 0), (0, size)], fill="white", width=1)

        # Top-right
        draw.line([(width-size-1, 0), (width-1, 0)], fill="white", width=1)
        draw.line([(width-1, 0), (width-1, size)], fill="white", width=1)

        # Bottom-left
        draw.line([(0, height-1), (size, height-1)], fill="white", width=1)
        draw.line([(0, height-size-1), (0, height-1)], fill="white", width=1)

        # Bottom-right
        draw.line([(width-size-1, height-1), (width-1, height-1)], fill="white", width=1)
        draw.line([(width-1, height-size-1), (width-1, height-1)], fill="white", width=1)

    @staticmethod
    def draw_progress_bar(draw, x, y, width, height, progress, style="geometric"):
        """Draw progress bar with tech aesthetic

        Args:
            style: "geometric" (filled rectangles) or "scan" (scanning line)
        """
        # Background bar
        draw.rectangle([(x, y), (x + width, y + height)], outline="white", fill="black")

        if style == "geometric":
            # Filled geometric pattern
            fill_width = int(width * progress)
            if fill_width > 0:
                # Main fill
                draw.rectangle([(x, y), (x + fill_width, y + height)], fill="white")

                # Add segmented look (every 8 pixels)
                for seg_x in range(x, x + fill_width, 8):
                    draw.line([(seg_x, y), (seg_x, y + height)], fill="black", width=1)

        elif style == "scan":
            # Scanning line effect
            scan_x = x + int(width * progress)
            if scan_x < x + width:
                draw.line([(scan_x, y), (scan_x, y + height)], fill="white", width=2)

    @staticmethod
    def draw_audio_bars(draw, x, y, width, height, levels, bar_count=10):
        """Draw vertical audio level bars

        Args:
            levels: List of float values 0.0-1.0 for each bar
        """
        bar_width = width // bar_count
        spacing = 1

        for i in range(bar_count):
            bar_x = x + i * bar_width

            # Get level for this bar (or 0 if not enough data)
            level = levels[i] if i < len(levels) else 0.0
            bar_height = int(height * level)

            if bar_height > 0:
                # Draw bar from bottom up
                bar_y = y + height - bar_height
                draw.rectangle([
                    (bar_x, bar_y),
                    (bar_x + bar_width - spacing, y + height)
                ], fill="white")

    @staticmethod
    def draw_scanning_line(draw, x, y, width, height, progress):
        """Draw animated scanning line effect"""
        scan_x = x + int(width * progress)

        # Main scan line
        draw.line([(scan_x, y), (scan_x, y + height)], fill="white", width=1)

        # Fading trail (3 pixels behind)
        for offset in range(1, 4):
            trail_x = scan_x - offset
            if trail_x >= x:
                # Fade by using dotted pattern
                if offset == 1:
                    draw.line([(trail_x, y), (trail_x, y + height)], fill="white", width=1)

    @staticmethod
    def draw_status_dots(draw, x, y, count=3, active=0, spacing=4):
        """Draw status indicator dots ●●●

        Args:
            active: Which dot is active (0-based, -1 for all inactive)
        """
        dot_radius = 2
        for i in range(count):
            dot_x = x + i * spacing
            fill = "white" if i == active else "black"
            outline = "white"

            draw.ellipse([
                (dot_x - dot_radius, y - dot_radius),
                (dot_x + dot_radius, y + dot_radius)
            ], fill=fill, outline=outline)

    @staticmethod
    def draw_angular_divider(draw, x, y, width):
        """Draw angular tech-style divider [========]"""
        # Left bracket
        draw.line([(x, y), (x + 2, y)], fill="white", width=1)

        # Main line
        draw.line([(x + 3, y), (x + width - 3, y)], fill="white", width=1)

        # Right bracket
        draw.line([(x + width - 2, y), (x + width, y)], fill="white", width=1)

    @staticmethod
    def draw_text_with_shadow(draw, position, text, font, shadow_offset=1):
        """Draw text with subtle shadow for depth"""
        x, y = position

        # Shadow (slightly offset)
        draw.text((x + shadow_offset, y + shadow_offset), text, fill="black", font=font)

        # Main text
        draw.text((x, y), text, fill="white", font=font)


class LoadingAnimation:
    """Animated loading screen for model initialization"""

    def __init__(self, width=128, height=32):
        self.width = width
        self.height = height
        self.state = AnimationState()
        self.stage = "INIT"
        self.stages = ["INIT", "LOADING MODEL", "READY"]
        self.stage_index = 0

    def update(self, progress, stage=None):
        """Update loading progress

        Args:
            progress: 0.0 to 1.0
            stage: Current loading stage text
        """
        if stage:
            self.stage = stage

        # Auto-advance stage based on progress
        if progress > 0.3 and self.stage_index == 0:
            self.stage_index = 1
            self.stage = self.stages[1]
        elif progress > 0.95 and self.stage_index == 1:
            self.stage_index = 2
            self.stage = self.stages[2]

        return progress

    def draw(self, draw, progress):
        """Draw loading animation frame"""
        # Clear background
        draw.rectangle([(0, 0), (self.width, self.height)], fill="black")

        # Corner brackets
        TechDrawing.draw_corner_brackets(draw, self.width, self.height)

        # Stage text at top
        stage_text = self.stage
        draw.text((8, 4), stage_text, fill="white")

        # Progress bar in middle
        bar_width = self.width - 16
        bar_height = 6
        bar_x = 8
        bar_y = 14
        TechDrawing.draw_progress_bar(draw, bar_x, bar_y, bar_width, bar_height,
                                      progress, style="geometric")

        # Percentage
        percentage = f"{int(progress * 100)}%"
        draw.text((self.width - 28, 22), percentage, fill="white")

        # Scanning line effect
        scan_progress = (progress * 2) % 1.0  # Scan faster than progress
        TechDrawing.draw_scanning_line(draw, 0, 0, self.width, self.height, scan_progress)


class AudioVisualizer:
    """Real-time audio level visualization"""

    def __init__(self, width=128, height=32, bar_count=10):
        self.width = width
        self.height = height
        self.bar_count = bar_count
        self.levels = [0.0] * bar_count
        self.peaks = [0.0] * bar_count
        self.peak_decay = 0.05  # How fast peaks fall

    def update(self, audio_level):
        """Update audio levels

        Args:
            audio_level: Single float 0.0-1.0 representing current audio RMS
        """
        # Shift levels left
        self.levels = self.levels[1:] + [audio_level]

        # Update peaks (hold then decay)
        for i in range(len(self.peaks)):
            if self.levels[i] > self.peaks[i]:
                self.peaks[i] = self.levels[i]
            else:
                self.peaks[i] = max(0.0, self.peaks[i] - self.peak_decay)

    def draw(self, draw, x, y, width, height):
        """Draw audio visualization bars"""
        TechDrawing.draw_audio_bars(draw, x, y, width, height,
                                    self.levels, self.bar_count)


class TransitionEffect:
    """Smooth transition effects between states"""

    def __init__(self, duration=0.3):
        self.duration = duration
        self.state = AnimationState()
        self.effect = "slide"  # "slide", "wipe", "fade"

    def start(self, effect="slide"):
        """Start transition animation"""
        self.effect = effect
        self.state.reset()

    def is_active(self):
        """Check if transition is in progress"""
        return not self.state.is_complete()

    def get_offset(self, width):
        """Get slide offset for transitioning content"""
        if self.effect == "slide":
            # Slide in from right
            return int(width * (1.0 - self.state.progress))
        return 0

    def apply_wipe(self, draw, width, height):
        """Apply wipe effect (cover old content)"""
        if self.effect == "wipe" and self.is_active():
            wipe_x = int(width * self.state.progress)
            draw.rectangle([(0, 0), (wipe_x, height)], fill="black")

    def update(self):
        """Update transition animation"""
        return self.state.update(self.duration)


def ease_out_cubic(t):
    """Easing function for smooth deceleration

    Args:
        t: Progress 0.0 to 1.0
    Returns:
        Eased progress 0.0 to 1.0
    """
    return 1 - pow(1 - t, 3)


def ease_in_out_sine(t):
    """Smooth sine-wave easing

    Args:
        t: Progress 0.0 to 1.0
    Returns:
        Eased progress 0.0 to 1.0
    """
    return -(math.cos(math.pi * t) - 1) / 2
