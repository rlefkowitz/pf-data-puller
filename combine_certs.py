import certifi

# Paths to the CA bundles
certifi_ca_bundle = certifi.where()
combined_ca_bundle = "combined-ca-bundle.crt"

# Read the original CA bundle
with open(certifi_ca_bundle, "rb") as infile:
    original_ca = infile.read()

# Read Zyte's CA certificate
with open("zyte-ca.crt", "rb") as infile:
    zyte_ca = infile.read()

# Combine and write to a new file
with open(combined_ca_bundle, "wb") as outfile:
    outfile.write(original_ca)
    outfile.write(b"\n")
    outfile.write(zyte_ca)
