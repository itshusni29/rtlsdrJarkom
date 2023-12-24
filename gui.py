import dearpygui.dearpygui as dpg
from spiritbox import SpiritBox
import threading
import numpy as np
import color_theme as ct

# Create an instance of the SpiritBox class
sb = SpiritBox()

# Callback function to start the spirit box in automatic mode
def start_spiritbox():
    start_freq = 88e6
    end_freq = 108e6
    step_freq = 0.2e6
    t = threading.Thread(target=sb.run_automatic_realtime, args=(start_freq, end_freq, step_freq))
    t.start()

# Callback function to stop the spirit box
def stop_spiritbox():
    sb.close()

# Callback function to set manual frequency
def set_manual_freq():
    freq = dpg.get_value("manual_freq")[0] * 1e6
    sb.set_manual_freq(freq)

# Create the Dear PyGui context
dpg.create_context()

# Create a viewport for the Dear PyGui window
dpg.create_viewport(title="SpiritBox", width=800, height=600, resizable=True)
dpg.setup_dearpygui()

# Create the main window
with dpg.window(label="Spirit Box", width=-1, height=-1, tag="main_window", on_close=stop_spiritbox) as main_window:
    dpg.add_text("The spirits greet you", parent=main_window)

    # Buttons to start and stop the spirit box
    dpg.add_button(label="Start", callback=start_spiritbox)
    dpg.add_button(label="Stop", callback=stop_spiritbox)

    dpg.add_spacer(height=10)

    # Display current frequency and controls for manual frequency
    dpg.add_text("Current Frequency: ", tag="current_freq")
    manual_freq_value = [88.0]
    dpg.add_input_floatx(label="Manual Frequency (MHz)", tag="manual_freq", default_value=manual_freq_value)
    dpg.add_button(label="Set Manual Frequency", callback=set_manual_freq)

    # Display speech buffer and audio plot
    dpg.add_text("The spirits say:", label="Speech Buffer", tag="text_buffer")
    with dpg.plot(label="Audio (Time Domain)", tag="audio_plot", width=-1, height=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="Sample", tag="x_axis")
        dpg.add_plot_axis(dpg.mvYAxis, label="int16", tag="y_axis")
        dpg.add_line_series(np.arange(len(sb.sample_buffer)), sb.sample_buffer, parent="y_axis", tag="audio_line")

# Define the color theme for the GUI
with dpg.theme() as theme:
    with dpg.theme_component(dpg.mvThemeCat_Core):
        dpg.add_theme_color(dpg.mvThemeCol_WindowBg, ct.VAMPIRE_BLACK)
        dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, ct.PUMPKIN)

# Apply the theme to the main window
dpg.bind_item_theme(main_window, theme)

# Show the Dear PyGui viewport and set the main window
dpg.show_viewport()
dpg.set_primary_window(main_window, True)

# Main loop to update the GUI and handle events
while dpg.is_dearpygui_running():
    # Update the displayed current frequency
    dpg.set_value("current_freq", f"Current Frequency: {sb.current_freq/1e6:.2f} MHz")

    # Update the displayed speech buffer
    if tbuf := sb.text_buffer:
        dpg.set_value("text_buffer", f"The spirits say: {tbuf}")

    # Update the audio plot with the sample buffer
    if sbuf := sb.sample_buffer:
        dpg.set_axis_limits("y_axis", np.iinfo(np.int16).min, np.iinfo(np.int16).max)
        dpg.set_axis_limits("x_axis", 0, len(sbuf))
        dpg.set_value("audio_line", [np.arange(len(sbuf)), sbuf])

    # Render the Dear PyGui frame
    dpg.render_dearpygui_frame()

# Destroy the Dear PyGui context
dpg.destroy_context()
