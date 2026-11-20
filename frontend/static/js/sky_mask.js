// HTML5 Canvas brush tool for painting horizon masks
const bgCanvas = document.getElementById("bgCanvas");
const drawCanvas = document.getElementById("drawCanvas");
const bgCtx = bgCanvas.getContext("2d");
const drawCtx = drawCanvas.getContext("2d");

const brushSizeInput = document.getElementById("brushSize");
const modeBtn = document.getElementById("modeBtn");
const clearBtn = document.getElementById("clearBtn");
const saveBtn = document.getElementById("saveBtn");
const statusMsg = document.getElementById("statusMsg");

let drawing = false;
let eraseMode = false;

// Draw a simulated night sky + horizon silhouette for Dev Mode
function drawSimulatedSky() {
  const w = bgCanvas.width;
  const h = bgCanvas.height;

  const grad = bgCtx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#020617");
  grad.addColorStop(1, "#0f172a");
  bgCtx.fillStyle = grad;
  bgCtx.fillRect(0, 0, w, h);

  // Simulated stars
  bgCtx.fillStyle = "#e2e8f0";
  for (let i = 0; i < 120; i++) {
    const x = Math.random() * w;
    const y = Math.random() * (h * 0.78);
    const r = Math.random() * 1.3;
    bgCtx.beginPath();
    bgCtx.arc(x, y, r, 0, Math.PI * 2);
    bgCtx.fill();
  }

  // Simulated treeline / roof silhouette along bottom
  bgCtx.fillStyle = "#090d16";
  bgCtx.beginPath();
  bgCtx.moveTo(0, h);
  bgCtx.lineTo(0, h - 90);
  bgCtx.lineTo(140, h - 120);
  bgCtx.lineTo(240, h - 75);
  bgCtx.lineTo(420, h - 110);
  bgCtx.lineTo(540, h - 65);
  bgCtx.lineTo(w, h - 95);
  bgCtx.lineTo(w, h);
  bgCtx.closePath();
  bgCtx.fill();
}

function getPos(e) {
  const rect = drawCanvas.getBoundingClientRect();
  const scaleX = drawCanvas.width / rect.width;
  const scaleY = drawCanvas.height / rect.height;
  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top) * scaleY,
  };
}

function paint(e) {
  if (!drawing) return;
  const { x, y } = getPos(e);
  drawCtx.globalCompositeOperation = eraseMode ? "destination-out" : "source-over";
  drawCtx.fillStyle = "rgba(239, 68, 68, 0.55)";
  drawCtx.beginPath();
  drawCtx.arc(x, y, Number(brushSizeInput.value), 0, Math.PI * 2);
  drawCtx.fill();
}

drawCanvas.addEventListener("mousedown", (e) => { drawing = true; paint(e); });
drawCanvas.addEventListener("mousemove", paint);
window.addEventListener("mouseup", () => { drawing = false; });

modeBtn.addEventListener("click", () => {
  eraseMode = !eraseMode;
  modeBtn.textContent = eraseMode ? "Mode: Eraser" : "Mode: Paint Mask";
});

clearBtn.addEventListener("click", () => {
  drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
});

saveBtn.addEventListener("click", async () => {
  // Build clean binary canvas: white = active sky, black = masked out
  const out = document.createElement("canvas");
  out.width = drawCanvas.width;
  out.height = drawCanvas.height;
  const outCtx = out.getContext("2d");

  outCtx.fillStyle = "#ffffff";
  outCtx.fillRect(0, 0, out.width, out.height);

  const maskPixels = drawCtx.getImageData(0, 0, out.width, out.height).data;
  const outImg = outCtx.getImageData(0, 0, out.width, out.height);
  for (let i = 0; i < maskPixels.length; i += 4) {
    if (maskPixels[i + 3] > 0) {
      outImg.data[i] = 0;
      outImg.data[i + 1] = 0;
      outImg.data[i + 2] = 0;
    }
  }
  outCtx.putImageData(outImg, 0, 0);

  const res = await fetch("/api/mask/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mask_data_url: out.toDataURL("image/png") }),
  });

  if (res.ok) {
    statusMsg.textContent = "Saved binary mask to data/config/sky_mask.png";
    statusMsg.classList.remove("hidden");
  }
});

drawSimulatedSky();