(function () {
  const cfg = window.PORTFOLIO_CONFIG || {};
  const product = cfg.product || {};

  function $(id) {
    return document.getElementById(id);
  }

  function setText(id, text) {
    const el = $(id);
    if (el && text) el.textContent = text;
  }

  function setHref(id, href) {
    const el = $(id);
    if (el && href) el.href = href;
  }

  // Config-driven content
  setText("aboutName", cfg.name);
  setText("footerName", cfg.name);
  setText("heroBadge", `${cfg.university || ""} · ${(cfg.degree || "").split("—").pop()?.trim() || "AI"}`);
  setText("aboutUni", cfg.university);
  setText("aboutDegree", cfg.degree);
  setText("productName", product.name);
  setText("pricingName", product.name);
  setText("productTagline", product.tagline);
  setText("pricingPrice", product.price);
  setText("pricingNote", product.priceNote);
  setText("year", new Date().getFullYear());

  setHref("contactEmail", `mailto:${cfg.email}`);
  setText("contactEmail", cfg.email);
  setHref("contactLinkedin", cfg.linkedin);
  setHref("contactGithub", cfg.github);

  const skills = [
    "Python", "Local LLMs", "Ollama", "RAG / ChromaDB", "Voice AI",
    "Multi-Agent Systems", "Data Analytics", "Whisper STT", "Windows Automation",
  ];
  const skillContainer = $("skillTags");
  if (skillContainer) {
    skills.forEach((s) => {
      const tag = document.createElement("span");
      tag.className = "skill-tag";
      tag.textContent = s;
      skillContainer.appendChild(tag);
    });
  }

  // Buy button
  const buyBtn = $("buyBtn");
  const salesEnabled = product.salesEnabled && product.buyUrl && !product.buyUrl.includes("your-product");

  if (buyBtn) {
    if (salesEnabled) {
      buyBtn.href = product.buyUrl;
      buyBtn.target = "_blank";
      buyBtn.rel = "noopener";
      buyBtn.textContent = `Buy now — ${product.price}`;
    } else {
      buyBtn.href = `mailto:${cfg.email}?subject=Spine%20AI%20Purchase%20Inquiry`;
      buyBtn.textContent = "Contact to purchase";
      buyBtn.classList.add("coming-soon");
    }
  }

  ["heroBuy", "navBuy"].forEach((id) => {
    const el = $(id);
    if (el && salesEnabled) {
      el.href = product.buyUrl;
      el.target = "_blank";
    }
  });

  // Mobile menu
  const menuBtn = $("menuBtn");
  const navLinks = $("navLinks");
  if (menuBtn && navLinks) {
    menuBtn.addEventListener("click", () => navLinks.classList.toggle("open"));
    navLinks.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", () => navLinks.classList.remove("open"));
    });
  }

  // Orb particles
  const container = $("orbParticles");
  if (container) {
    const colors = ["#00e8ff", "#c77dff", "#e040fb", "#9d4edd", "#48cae4", "#ff6bcb"];
    for (let i = 0; i < 28; i++) {
      const dot = document.createElement("span");
      const angle = (i / 28) * Math.PI * 2;
      const r = 30 + Math.random() * 28;
      dot.style.left = `${50 + Math.cos(angle) * r}%`;
      dot.style.top = `${50 + Math.sin(angle) * r}%`;
      dot.style.background = colors[i % colors.length];
      dot.style.color = colors[i % colors.length];
      dot.style.animationDelay = `${Math.random() * 2}s`;
      dot.style.width = `${4 + Math.random() * 4}px`;
      dot.style.height = dot.style.width;
      container.appendChild(dot);
    }
  }
})();
