// ==========================================
// 1. DYNAMIC INTERACTIVE P2P MESH CANVAS
// ==========================================
const canvas = document.getElementById('particles-canvas');
if (canvas) {
  const ctx = canvas.getContext('2d');
  let width, height, particles;
  let mouse = { x: null, y: null, radius: 150 };

  function initCanvas() {
    width = canvas.width = window.innerWidth;
    height = canvas.height = window.innerHeight;
    particles = [];
    const count = Math.min(Math.floor((width * height) / 22000), 50);

    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        radius: Math.random() * 2 + 1.2,
      });
    }
  }

  function animateCanvas() {
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < particles.length; i++) {
      const p1 = particles[i];
      p1.x += p1.vx;
      p1.y += p1.vy;

      if (p1.x < 0 || p1.x > width) p1.vx *= -1;
      if (p1.y < 0 || p1.y > height) p1.vy *= -1;

      // Mouse attraction
      if (mouse.x !== null && mouse.y !== null) {
        const dx = mouse.x - p1.x;
        const dy = mouse.y - p1.y;
        const dist = Math.hypot(dx, dy);
        if (dist < mouse.radius) {
          const force = (mouse.radius - dist) / mouse.radius;
          p1.x += (dx / dist) * force * 1.2;
          p1.y += (dy / dist) * force * 1.2;
        }
      }

      ctx.beginPath();
      ctx.arc(p1.x, p1.y, p1.radius, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(129, 140, 248, 0.45)';
      ctx.fill();

      // Draw mesh vectors between neighboring nodes
      for (let j = i + 1; j < particles.length; j++) {
        const p2 = particles[j];
        const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
        if (dist < 130) {
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.strokeStyle = `rgba(99, 102, 241, ${0.2 * (1 - dist / 130)})`;
          ctx.lineWidth = 0.75;
          ctx.stroke();
        }
      }
    }

    requestAnimationFrame(animateCanvas);
  }

  window.addEventListener('resize', initCanvas);
  window.addEventListener('mousemove', (e) => {
    mouse.x = e.clientX;
    mouse.y = e.clientY;
  });
  window.addEventListener('mouseleave', () => {
    mouse.x = null;
    mouse.y = null;
  });

  initCanvas();
  animateCanvas();
}



// ==========================================
// 3. INTERSECTION OBSERVER SCROLL REVEAL
// ==========================================
const revealObserver = new IntersectionObserver(
  (entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const delay = el.getAttribute('data-delay') || 0;
        setTimeout(() => {
          el.classList.add('is-revealed');
        }, parseInt(delay, 10));
        observer.unobserve(el);
      }
    });
  },
  { rootMargin: '0px 0px -40px 0px', threshold: 0.1 }
);

document.querySelectorAll('[data-reveal]').forEach((el) => {
  revealObserver.observe(el);
});

// ==========================================
// 4. 3D MAGNETIC TILT & CURSOR SPOTLIGHT
// ==========================================
document.querySelectorAll('.system-card, .system-board, .download-card-hero').forEach((card) => {
  card.addEventListener('mousemove', (e) => {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    card.style.setProperty('--mouse-x', `${x}px`);
    card.style.setProperty('--mouse-y', `${y}px`);

    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / centerY) * -4;
    const rotateY = ((x - centerX) / centerX) * 4;

    card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(4px)`;
  });

  card.addEventListener('mouseleave', () => {
    card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px)';
  });
});

// ==========================================
// 5. INTERACTIVE PROTOCOL SCHEMA INSPECTOR
// ==========================================
const schemaData = {
  chat: {
    title: "Broadcast & Room Messaging Envelope",
    desc: "Carries encrypted message payloads with Lamport logical clock timestamps for deterministic causal ordering across asynchronous nodes.",
    props: [
      { name: "type", type: "string (enum)", desc: "'CHAT' | 'GROUP_MSG'" },
      { name: "msg_id", type: "UUIDv4", desc: "Unique message identifier for idempotent dedup" },
      { name: "lamport_time", type: "uint64", desc: "Logical clock tick value L(e)" },
      { name: "sender_id", type: "UUIDv4", desc: "Cryptographic peer identity" },
      { name: "payload.text", type: "string", desc: "Fernet-encrypted plaintext ciphertext" }
    ],
    code: `{
  "type": "CHAT",
  "msg_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "sender_id": "d3b07384-d113-4cd2-b7ca-4b0d0c384e56",
  "sender_name": "Alice",
  "lamport_time": 42,
  "timestamp": "10:04",
  "payload": {
    "text": "Encrypted symmetric message payload"
  }
}`
  },
  vote: {
    title: "Distributed Ballot & Consensus Packet",
    desc: "Transmits secret ballot choices to the election leader node. Peers verify election duration against internal clocks to eliminate late ballots.",
    props: [
      { name: "type", type: "string", desc: "'VOTE' | 'POLL_START' | 'POLL_RESULT'" },
      { name: "payload.poll_id", type: "UUIDv4", desc: "Unique poll election identifier" },
      { name: "payload.choice", type: "integer", desc: "Zero-indexed option index chosen" },
      { name: "sender_id", type: "UUIDv4", desc: "Voter identity hash preventing double voting" }
    ],
    code: `{
  "type": "VOTE",
  "msg_id": "a4f89d31-41b2-4cd8-89fa-1284e91209cc",
  "sender_id": "8f4b2384-e912-4aa3-88bb-4c0a1b283e11",
  "sender_name": "Bob",
  "lamport_time": 43,
  "payload": {
    "poll_id": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
    "choice": 0
  }
}`
  },
  file: {
    title: "Chunked Binary File Transfer Envelope",
    desc: "Transfers arbitrary files across the socket mesh in 32 KB chunked base64 envelopes with SHA-256 integrity verification upon completion.",
    props: [
      { name: "type", type: "string", desc: "'FILE_START' | 'FILE_CHUNK' | 'FILE_COMPLETE'" },
      { name: "payload.file_id", type: "UUIDv4", desc: "File transmission stream ID" },
      { name: "payload.chunk_index", type: "integer", desc: "Sequence index of current binary chunk" },
      { name: "payload.chunk_data", type: "base64", desc: "32 KB binary data stream slice" }
    ],
    code: `{
  "type": "FILE_CHUNK",
  "msg_id": "f5e1a90c-7b19-482b-8a21-9988ff220011",
  "sender_id": "d3b07384-d113-4cd2-b7ca-4b0d0c384e56",
  "lamport_time": 45,
  "payload": {
    "file_id": "2c5a2c3a-883e-4b21-8f43-7744aa991122",
    "chunk_index": 2,
    "chunk_data": "iVBORw0KGgoAAAANSUhEUgAA..."
  }
}`
  },
  discovery: {
    title: "UDP Broadcast Presence Beacon",
    desc: "Periodically emitted across subnet broadcast addresses to establish zero-configuration full-mesh TCP peering with neighboring local nodes.",
    props: [
      { name: "type", type: "string", desc: "'DISCOVERY_BEACON'" },
      { name: "listen_port", type: "uint16", desc: "TCP server listening port (6000-6030)" },
      { name: "sender_name", type: "string", desc: "Peer human-readable username" },
      { name: "sender_id", type: "UUIDv4", desc: "Unique node identifier" }
    ],
    code: `{
  "type": "DISCOVERY_BEACON",
  "sender_id": "d3b07384-d113-4cd2-b7ca-4b0d0c384e56",
  "sender_name": "Alice",
  "listen_port": 6000
}`
  }
};

function switchSchemaTab(tabName) {
  document.querySelectorAll('.schema-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });

  const data = schemaData[tabName];
  if (!data) return;

  const titleEl = document.getElementById('schema-title');
  const descEl = document.getElementById('schema-desc');
  const codeEl = document.getElementById('schema-code');
  const propsList = document.getElementById('schema-props');

  if (titleEl) titleEl.textContent = data.title;
  if (descEl) descEl.textContent = data.desc;
  if (codeEl) codeEl.textContent = data.code;

  if (propsList) {
    propsList.innerHTML = '';
    data.props.forEach(p => {
      const li = document.createElement('li');
      li.className = 'schema-prop-item';
      li.innerHTML = `<span class="prop-name">${p.name}</span> <span class="prop-type">${p.type}</span> — <span>${p.desc}</span>`;
      propsList.appendChild(li);
    });
  }
}

document.querySelectorAll('.schema-tab-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    switchSchemaTab(e.currentTarget.dataset.tab);
  });
});

switchSchemaTab('chat');

// ==========================================
// 6. LIVE TELEMETRY STREAM
// ==========================================
const streamEl = document.getElementById('telemetry-stream');
if (streamEl) {
  const telemetryEvents = [
    { t: '11:08:12', tag: 'NET', cls: 't-tag-sys', text: 'TCP Listener initialized on 0.0.0.0:6000 (Mesh Ready)' },
    { t: '11:08:13', tag: 'SEC', cls: 't-tag-sec', text: 'PBKDF2HMAC Key derived (100k iters). Fingerprint: #4B2F' },
    { t: '11:08:14', tag: 'UDP', cls: 't-tag-sys', text: 'Beacon broadcasted to 255.255.255.255:60001' },
    { t: '11:08:15', tag: 'MESH', cls: 't-tag-sec', text: 'Inbound peer handshake accepted from 192.168.1.104:6002 (Alice)' },
    { t: '11:08:17', tag: 'CLOCK', cls: 't-tag-clk', text: 'Causal event received: L_msg=14 -> Local Clock advanced to L=15' },
    { t: '11:08:19', tag: 'VOTE', cls: 't-tag-vote', text: 'Election started: "Protocol Migration" (Duration: 30s)' },
    { t: '11:08:22', tag: 'CONSENSUS', cls: 't-tag-vote', text: 'Vote tally verified. Consensus state: [Approved: 100%]' },
    { t: '11:08:26', tag: 'FILE', cls: 't-tag-sys', text: 'Chunked stream complete: report.pdf (128 KB) -> SHA-256 Verified OK' }
  ];

  let eventIdx = 0;
  function pushTelemetry() {
    if (eventIdx >= telemetryEvents.length) {
      streamEl.innerHTML = '';
      eventIdx = 0;
    }
    const ev = telemetryEvents[eventIdx++];
    const div = document.createElement('div');
    div.className = 'terminal-line';
    div.innerHTML = `
      <span class="t-time">[${ev.t}]</span> 
      <span class="${ev.cls}">[${ev.tag}]</span> 
      <span>${ev.text}</span>
    `;
    streamEl.appendChild(div);
    streamEl.scrollTop = streamEl.scrollHeight;

    setTimeout(pushTelemetry, Math.floor(Math.random() * 800) + 1200);
  }
  setTimeout(pushTelemetry, 500);
}

// ==========================================
// 7. DOWNLOAD BUTTON FEEDBACK
// ==========================================
document.querySelectorAll('.btn-download-trigger').forEach(btn => {
  btn.addEventListener('click', () => {
    const orig = btn.innerHTML;
    setTimeout(() => {
      btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> <span>Downloading... Check Downloads Folder</span>`;
      setTimeout(() => {
        btn.innerHTML = orig;
      }, 4000);
    }, 150);
  });
});
