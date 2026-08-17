FROM barichello/godot-ci:4.2.2

WORKDIR /project

# Install xvfb for headless rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Godot headless export templates are included in the base image

EXPOSE 6080 5900

# Run with xvfb for headless operation
ENTRYPOINT ["xvfb-run", "-a", "-s", "-screen 0 1024x768x24"]
CMD ["godot", "--headless", "--main-pack", "/project/game.pck"]