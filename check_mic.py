#!/usr/bin/env python3
"""
Microphone Diagnostic Utility for Lanite.

This script helps diagnose audio hardware issues by:
1. Listing all available audio devices
2. Showing default input device details
3. Recording a test sample to verify microphone functionality

Usage:
    python utils/check_mic.py
"""

import sounddevice as sd
import numpy as np
import time
import sys

# Try to import soundfile for saving test recordings
try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


def list_audio_devices():
    """
    List all available audio input/output devices.
    """
    print("=" * 60)
    print("AVAILABLE AUDIO DEVICES")
    print("=" * 60)
    
    devices = sd.query_devices()
    
    for i, device in enumerate(devices):
        # Mark default devices
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        
        marker = ""
        if i == default_input:
            marker = " [DEFAULT INPUT]"
        elif i == default_output:
            marker = " [DEFAULT OUTPUT]"
        
        # Show device info
        print(f"\n[{i}]{marker}")
        print(f"  Name: {device['name']}")
        print(f"  Inputs: {device['max_input_channels']}")
        print(f"  Outputs: {device['max_output_channels']}")
        print(f"  Sample Rate: {device['default_samplerate']} Hz")
        print(f"  Host API: {sd.query_hostapis(device['hostapi'])['name']}")


def show_default_device():
    """
    Display detailed information about the default input device.
    """
    print("\n" + "=" * 60)
    print("DEFAULT INPUT DEVICE DETAILS")
    print("=" * 60)
    
    try:
        default_input = sd.query_devices(kind='input')
        print(f"\n  Name: {default_input['name']}")
        print(f"  Channels: {default_input['max_input_channels']}")
        print(f"  Sample Rate: {default_input['default_samplerate']} Hz")
        print(f"  Host API: {sd.query_hostapis(default_input['hostapi'])['name']}")
    except Exception as e:
        print(f"\n  Error getting default device: {e}")


def test_recording(duration=3, sample_rate=16000):
    """
    Record a test sample from the microphone.
    
    Args:
        duration: Recording duration in seconds
        sample_rate: Audio sample rate in Hz
    """
    print("\n" + "=" * 60)
    print("RECORDING TEST")
    print("=" * 60)
    
    print(f"\n  Sample Rate: {sample_rate} Hz")
    print(f"  Duration: {duration} seconds")
    print(f"  Channels: 1 (mono)")
    
    print("\n  Recording in 3 seconds... Speak into your microphone!")
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)
    
    print("\n  🎤 Recording...")
    
    try:
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype='float32'
        )
        sd.wait()  # Wait until recording is finished
        
        print("  ✅ Recording complete!")
        
        # Analyze recording
        max_amplitude = np.max(np.abs(recording))
        rms_amplitude = np.sqrt(np.mean(recording ** 2))
        
        print(f"\n  AUDIO ANALYSIS:")
        print(f"  Max Amplitude: {max_amplitude:.4f}")
        print(f"  RMS Amplitude: {rms_amplitude:.4f}")
        
        # Interpret results
        print(f"\n  INTERPRETATION:")
        if max_amplitude < 0.001:
            print("  ⚠️  Very low audio - microphone may not be working")
            print("      Check if microphone is muted or disconnected")
        elif max_amplitude < 0.01:
            print("  ⚠️  Low audio - consider increasing microphone volume")
        elif max_amplitude > 0.9:
            print("  ⚠️  Audio is clipping - reduce microphone volume")
        else:
            print("  ✅ Audio levels look good!")
        
        # Save recording if soundfile is available
        if HAS_SOUNDFILE:
            filename = "test_recording.wav"
            sf.write(filename, recording, sample_rate)
            print(f"\n  Saved test recording to: {filename}")
        else:
            print("\n  Note: Install 'soundfile' to save test recordings")
            print("        pip install soundfile")
        
    except Exception as e:
        print(f"  ❌ Recording failed: {e}")


def check_sample_rate_compatibility(target_rate=16000):
    """
    Check if the default device supports the target sample rate.
    
    Args:
        target_rate: Desired sample rate to test
    """
    print("\n" + "=" * 60)
    print("SAMPLE RATE COMPATIBILITY")
    print("=" * 60)
    
    try:
        default_device = sd.query_devices(kind='input')
        native_rate = int(default_device['default_samplerate'])
        
        print(f"\n  Native Sample Rate: {native_rate} Hz")
        print(f"  Target Sample Rate: {target_rate} Hz")
        
        if native_rate == target_rate:
            print("  ✅ Native rate matches target - optimal configuration")
        elif native_rate % target_rate == 0 or target_rate % native_rate == 0:
            print("  ✅ Rates are compatible - resampling will work")
        else:
            print("  ⚠️  Rates may not be integer multiples")
            print("      Resampling quality may vary")
        
        # Test actual recording at target rate
        print(f"\n  Testing {target_rate} Hz recording...")
        try:
            test = sd.rec(
                int(0.1 * target_rate),
                samplerate=target_rate,
                channels=1
            )
            sd.wait()
            print("  ✅ Recording at target rate successful")
        except Exception as e:
            print(f"  ❌ Recording at target rate failed: {e}")
        
    except Exception as e:
        print(f"  Error checking sample rate: {e}")


def main():
    """
    Run all diagnostic tests.
    """
    print("\n" + "=" * 60)
    print("  LANITE MICROPHONE DIAGNOSTIC UTILITY")
    print("=" * 60)
    
    # List all devices
    list_audio_devices()
    
    # Show default device details
    show_default_device()
    
    # Check sample rate compatibility
    check_sample_rate_compatibility()
    
    # Run recording test
    print("\n  Would you like to run a recording test? (y/n): ", end="")
    try:
        response = input().strip().lower()
        if response == 'y':
            test_recording()
    except EOFError:
        print("n")
        print("  Skipping recording test")
    
    print("\n" + "=" * 60)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print("\n  If you see issues:")
    print("  1. Check Windows Settings > Privacy > Microphone")
    print("  2. Ensure Python has microphone access")
    print("  3. Try a different microphone device")
    print("  4. Check microphone volume in Sound Settings")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDiagnostic interrupted by user.")
        sys.exit(0)
