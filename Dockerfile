# Apify Python + Playwright base image (includes Chromium and all system deps)
FROM apify/actor-python-playwright:3.11

# Copy and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install patchright's patched Chromium
RUN python -m patchright install chromium

# Copy all source files
COPY . ./

# Run the Apify actor
CMD ["python", "main.py"]
