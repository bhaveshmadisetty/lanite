"""
Visual popup indicator for Lanite.

Provides a non-intrusive UI element that appears when recording
is active, positioned in the bottom-right corner of the screen.

Threading Note:
    Tkinter requires UI operations to run on the main thread.
    The init() function should be called from the main thread,
    and show()/hide() use .after() for thread-safe updates.
"""

import tkinter as tk

# Global reference to the popup window
_root = None


def init():
    """
    Initialize the popup window.
    
    Creates a borderless, always-on-top window positioned in
    the bottom-right corner of the screen. The window starts
    hidden and is shown/hidden via show() and hide() functions.
    
    This function runs Tkinter's mainloop(), so it should be
    called from the main thread.
    """
    global _root
    
    # Create main window
    _root = tk.Tk()
    
    # Remove window decorations (title bar, borders)
    _root.overrideredirect(True)
    
    # Keep window on top of all other windows
    _root.attributes("-topmost", True)
    
    # Set background color
    _root.configure(bg="black")
    
    # Create label with recording indicator
    label = tk.Label(
        _root,
        text="🎤 Listening",
        fg="white",
        bg="black",
        font=("Segoe UI", 10)
    )
    label.pack(ipadx=10, ipady=5)
    
    # Calculate position (bottom-right corner)
    _root.update_idletasks()
    screen_w = _root.winfo_screenwidth()
    screen_h = _root.winfo_screenheight()
    
    # Position with small margin from edges
    x_pos = screen_w - 170
    y_pos = screen_h - 100
    _root.geometry(f"+{x_pos}+{y_pos}")
    
    # Start hidden
    _root.withdraw()
    
    # Run the event loop (blocking)
    _root.mainloop()


def show():
    """
    Show the popup window.
    
    Uses .after() to schedule the show operation on the main
    thread, making this function safe to call from any thread.
    """
    if _root:
        _root.after(0, _root.deiconify)


def hide():
    """
    Hide the popup window.
    
    Uses .after() to schedule the hide operation on the main
    thread, making this function safe to call from any thread.
    """
    if _root:
        _root.after(0, _root.withdraw)


def update_text(text):
    """
    Update the popup text.
    
    Args:
        text: New text to display in the popup
    """
    if _root:
        for widget in _root.winfo_children():
            if isinstance(widget, tk.Label):
                widget.config(text=text)
