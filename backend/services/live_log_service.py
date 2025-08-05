import subprocess
import select


# Paths and code logics are hidden due to confidentiality...
#Summary: This code defines a service to stream logs from a device over SSH. It uses a generator to yield log lines in real-time, allowing for efficient streaming of log data.
class LiveLogService:
    def __init__(self):
        pass

    def stream_log_for_ip(self, pump_ip):
        """
        Establishes an SSH connection to the given IP and streams the content
        of the PowerlogFile.txt using a generator.

        This method assumes that passwordless SSH (e.g., using public keys)
        is configured for the target device.
        """
        # Command to stream the log file via SSH.
        # -o StrictHostKeyChecking=no bypasses the host key verification prompt.
        ssh_command = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            f"root@{pump_ip}",
            # path jhidden due to confidentiality...
        ]
        
        process = subprocess.Popen(
            ssh_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        try:
            # Read line by line from stdout
            for line in process.stdout:
                yield f"data: {line.strip()}\n\n"
            # After stdout closes, check stderr for any remaining output
            for line in process.stderr:
                yield f"data: ERROR: {line.strip()}\n\n"

        except GeneratorExit:
            print(f"Client disconnected from {pump_ip}. Closing SSH connection.")
        except Exception as e:
            print(f"An error occurred while streaming logs from {pump_ip}: {e}")
            yield f"data: ERROR: {str(e)}\n\n"
        finally:
            print(f"Terminating subprocess for {pump_ip}.")
            process.terminate()
            process.wait()
