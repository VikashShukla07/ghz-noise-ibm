"""Save your IBM Quantum credentials on this computer (run once).

You need two things from https://quantum.cloud.ibm.com :
  1. an API key   (dashboard -> "Create API key")
  2. your instance CRN (dashboard -> "Instances" -> copy the CRN of your free/open instance)

Run:
    python scripts/save_ibm_account.py
and paste them when asked. They are stored in your user folder (~/.qiskit),
NOT in this project, so they never end up on GitHub.
"""

from getpass import getpass

from qiskit_ibm_runtime import QiskitRuntimeService

token = getpass("Paste your IBM Quantum API key (hidden): ").strip()
instance = input("Paste your instance CRN: ").strip()

try:
    QiskitRuntimeService.save_account(
        channel="ibm_quantum_platform", token=token, instance=instance, set_as_default=True, overwrite=True
    )
except Exception as err:  # older qiskit-ibm-runtime versions call this channel "ibm_cloud"
    print(f"'ibm_quantum_platform' channel failed ({err}); trying 'ibm_cloud'...")
    QiskitRuntimeService.save_account(
        channel="ibm_cloud", token=token, instance=instance, set_as_default=True, overwrite=True
    )

service = QiskitRuntimeService()
print("Saved. Devices you can use:")
for b in service.backends(simulator=False, operational=True):
    print(f"  {b.name}: {b.num_qubits} qubits, {b.status().pending_jobs} jobs waiting")
