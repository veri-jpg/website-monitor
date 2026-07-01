# Official Playwright image: semua system library browser sudah pre-installed,
# tidak perlu apt-get manual atau --with-deps.
FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install browser binary yang cocok dengan versi playwright yang baru di-pip-install.
# --with-deps tidak diperlukan karena deps sudah ada di base image.
RUN playwright install chromium

COPY . .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["sh", "entrypoint.sh"]