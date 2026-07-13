/* keystone/ui/static/lib/neuro3d.js
   NeuroHem — Illustrative Anatomical Brain Model (research-grade STYLE, procedural).
   NOT a patient scan, NOT a segmentation, NOT a detected bleed, NOT measured from
   any image. Every structure is an approximate procedural illustration.

   Fixed coordinate convention (define ONCE):
     X = left <-> right      (sagittal plane normal)
     Y = inferior <-> superior (axial plane normal)
     Z = anterior <-> posterior (coronal plane normal)

   Exposes window.Neuro3D = { initTwin, initCellScene }. Pure three.js (r128);
   defensive if THREE is missing or WebGL is unavailable (static fallback). */
(function () {
  "use strict";
  const OK = typeof THREE !== "undefined";

  // anatomical palette — quiet medical colors, no neon
  const C = {
    cortex: 0xc6a3a0, cortexR: 0xc19b98, wm: 0xe9e1cf, deep: 0xb98f93,
    thal: 0xb59aa6, hippo: 0xc7a98f, ventricle: 0x2a2f3a, callosum: 0xe3d8c4,
    cere: 0xbf9ea0, stem: 0xad9088, meninges: 0xd9cfc4,
    artery: 0xb25560, vein: 0x5f7fa5, capillary: 0x9a6a72,
    hemo: 0x7a1420, hemo2: 0xa5202e, edema: 0xd9a441,
    mri: 0x9aa0aa, ct_tissue: 0x2b2f36, ct_bone: 0xf0efe8, ct_blood: 0xffffff,
  };

  function webglOK() {
    try {
      const c = document.createElement("canvas");
      return !!(window.WebGLRenderingContext &&
        (c.getContext("webgl") || c.getContext("experimental-webgl")));
    } catch (e) { return false; }
  }

  function fallback(host, label) {
    host.innerHTML =
      '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;' +
      'flex-direction:column;gap:10px;color:#93a2c4;font-family:ui-monospace,monospace;font-size:12px;text-align:center;padding:20px">' +
      '<svg width="150" height="120" viewBox="0 0 150 120" fill="none">' +
      '<ellipse cx="75" cy="60" rx="60" ry="44" fill="#3a3236" stroke="#6a5a5f" stroke-width="2"/>' +
      '<path d="M75 18 Q75 60 75 102" stroke="#6a5a5f" stroke-width="1.5"/>' +
      '<ellipse cx="60" cy="66" rx="9" ry="7" fill="#7a1420"/>' +
      '<ellipse cx="90" cy="95" rx="20" ry="10" fill="#4a4247"/></svg>' +
      '<div>' + (label || "Illustrative Anatomical Brain Model") + '</div>' +
      '<div style="color:#5f6f92">static illustration — WebGL unavailable · not a patient scan</div></div>';
    return {
      setLayer(){}, isolateLobe(){}, setSlice(){}, setImaging(){},
      setHemorrhage(){}, setTime(){}, dispose(){},
    };
  }

  /* ---------------- controlled cortical folds (NOT stochastic noise) ---------
     Low-frequency, hemisphere-mirrored sulci running mostly antero-posterior.
     `side` = +1 (right) or -1 (left) so folds mirror across the midline. */
  function foldCortex(geo, side) {
    const p = geo.attributes.position, v = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i);
      const n = v.clone().normalize();
      // a few controlled sinusoids; low k => broad gyri, not noise
      const s =
        0.085 * Math.sin(3.0 * n.z + 2.2) * Math.cos(2.2 * n.y) +
        0.055 * Math.sin(4.0 * n.z * side + n.y) +
        0.045 * Math.cos(3.4 * n.y + 1.1);
      v.addScaledVector(n, s);
      v.x *= 1.02; v.y *= 0.96; v.z *= 1.12;   // gentle ovoid
      p.setXYZ(i, v.x, v.y, v.z);
    }
    geo.computeVertexNormals();
    return geo;
  }

  function initTwin(host, opts) {
    opts = opts || {};
    if (!OK || !webglOK()) return fallback(host, "Illustrative Anatomical Brain Model");
    const W = host.clientWidth, H = host.clientHeight || 520;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 100);
    camera.position.set(0, 0.2, 10.2);
    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch (e) { return fallback(host, "Illustrative Anatomical Brain Model"); }
    renderer.setSize(W, H); renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.localClippingEnabled = true; host.appendChild(renderer.domElement);

    // soft studio lighting — warm key + cool fill + hemisphere, NO colored glow
    scene.add(new THREE.HemisphereLight(0xf4efe6, 0x1b1c20, 0.65));
    const key = new THREE.DirectionalLight(0xfff4e8, 0.85); key.position.set(4, 6, 5); scene.add(key);
    const fill = new THREE.DirectionalLight(0xbcd0f0, 0.35); fill.position.set(-5, -1, -3); scene.add(fill);

    const pivot = new THREE.Group(); scene.add(pivot);       // for pan
    const brain = new THREE.Group(); pivot.add(brain);       // for rotate

    const mats = [];                                          // all materials (for clipping)
    const mk = (o) => { const m = new THREE.MeshStandardMaterial(o); mats.push(m); return m; };
    const orig = new Map();                                   // original colors for imaging restore

    // ---- cortex: two hemispheres, each a THREE.LOD (hi/lo), shared material ----
    function hemisphere(side, color) {
      const M = mk({ color, roughness: 0.86, metalness: 0.0, flatShading: false,
        transparent: true, opacity: 1.0 });
      orig.set(M, color);
      const hi = foldCortex(new THREE.SphereGeometry(1.9, 96, 96), side);
      const lo = foldCortex(new THREE.SphereGeometry(1.9, 30, 30), side);
      const lod = new THREE.LOD();
      lod.addLevel(new THREE.Mesh(hi, M), 0);
      lod.addLevel(new THREE.Mesh(lo, M), 9);
      lod.scale.set(1, 1, 1);
      lod.position.x = side * 0.98;                            // split L/R with fissure gap
      return { lod, M };
    }
    const R = hemisphere(1, C.cortex), L = hemisphere(-1, C.cortexR);
    const cortex = new THREE.Group(); cortex.add(R.lod, L.lod); brain.add(cortex);

    // lobe highlight caps (approximate) — hidden until isolated
    const lobes = new THREE.Group(); brain.add(lobes);
    function lobeCap(name, pos, scale, color) {
      const M = mk({ color, roughness: 0.7, transparent: true, opacity: 0.0, emissive: color, emissiveIntensity: 0.15 });
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.9, 24, 24), M);
      m.position.set(...pos); m.scale.set(...scale); m.userData.lobe = name; lobes.add(m); return m;
    }
    lobeCap("frontal", [0, 0.3, 1.5], [1.5, 1.1, 0.9], 0xd7b58a);
    lobeCap("parietal", [0, 1.2, -0.2], [1.6, 0.8, 1.1], 0x9ec6b0);
    lobeCap("temporal", [1.4, -0.7, 0.3], [0.9, 0.8, 1.3], 0xc79ab0);
    lobeCap("temporal_l", [-1.4, -0.7, 0.3], [0.9, 0.8, 1.3], 0xc79ab0);
    lobeCap("occipital", [0, 0.2, -1.7], [1.3, 1.0, 0.8], 0x9aa9d0);

    // ---- interior (revealed on slice) ----
    const interior = new THREE.Group(); brain.add(interior);
    const wmM = mk({ color: C.wm, roughness: 0.8, transparent: true, opacity: 0.92 }); orig.set(wmM, C.wm);
    const wm = new THREE.Mesh(new THREE.SphereGeometry(1.45, 48, 48), wmM);
    wm.scale.set(1.7, 0.95, 1.15); interior.add(wm);
    // corpus callosum
    const ccM = mk({ color: C.callosum, roughness: 0.7 }); orig.set(ccM, C.callosum);
    const cc = new THREE.Mesh(new THREE.TorusGeometry(0.7, 0.12, 12, 40, Math.PI), ccM);
    cc.rotation.x = Math.PI / 2; cc.position.set(0, 0.15, 0); interior.add(cc);
    // lateral ventricles (paired, dark) — shift under mass effect
    const ventM = mk({ color: C.ventricle, roughness: 0.4, transparent: true, opacity: 0.9 });
    const ventL = new THREE.Mesh(new THREE.SphereGeometry(0.34, 24, 24), ventM);
    ventL.scale.set(1.6, 0.7, 0.7); ventL.position.set(-0.35, 0.2, 0.05);
    const ventR = ventL.clone(); ventR.position.x = 0.35; interior.add(ventL, ventR);
    // deep nuclei (paired) — thalamus, basal ganglia, hippocampus, amygdala
    const deep = new THREE.Group(); interior.add(deep);
    function nucleus(name, color, pos, scale) {
      const M = mk({ color, roughness: 0.65, transparent: true, opacity: 0.95 }); orig.set(M, color);
      const m = new THREE.Mesh(new THREE.SphereGeometry(0.26, 24, 24), M);
      m.position.set(...pos); if (scale) m.scale.set(...scale); m.userData.region = name; deep.add(m); return m;
    }
    nucleus("thalamus", C.thal, [-0.28, 0.05, -0.05], [1.1, 1.0, 1.2]);
    nucleus("thalamus", C.thal, [0.28, 0.05, -0.05], [1.1, 1.0, 1.2]);
    nucleus("hypothalamus", 0xbfa0a8, [0, -0.35, 0.05], [1.3, 0.6, 0.9]);
    nucleus("basal ganglia", 0xc09aa2, [-0.55, -0.02, 0.35]);
    nucleus("basal ganglia", 0xc09aa2, [0.55, -0.02, 0.35]);
    nucleus("hippocampus", C.hippo, [-0.9, -0.45, -0.1], [1.7, 0.55, 0.8]);
    nucleus("hippocampus", C.hippo, [0.9, -0.45, -0.1], [1.7, 0.55, 0.8]);
    nucleus("amygdala", 0xb98f8c, [-0.95, -0.35, 0.5], [0.8, 0.8, 0.8]);
    nucleus("amygdala", 0xb98f8c, [0.95, -0.35, 0.5], [0.8, 0.8, 0.8]);

    // cerebellum (foliated) + brainstem (pons + medulla)
    const cereGeo = new THREE.SphereGeometry(0.72, 48, 48);
    (function foliate(g) { const p = g.attributes.position, v = new THREE.Vector3();
      for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); const n = v.clone().normalize();
        v.addScaledVector(n, 0.05 * Math.sin(18 * n.y)); p.setXYZ(i, v.x, v.y, v.z); } g.computeVertexNormals(); })(cereGeo);
    const cereM = mk({ color: C.cere, roughness: 0.85 }); orig.set(cereM, C.cere);
    const cere = new THREE.Mesh(cereGeo, cereM); cere.scale.set(1.3, 0.6, 0.8); cere.position.set(0, -1.55, -1.5);
    const stemM = mk({ color: C.stem, roughness: 0.7 }); orig.set(stemM, C.stem);
    const pons = new THREE.Mesh(new THREE.SphereGeometry(0.3, 24, 24), stemM); pons.scale.set(0.9, 0.7, 1.0); pons.position.set(0, -1.7, -0.7);
    const medulla = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.14, 1.0, 20), stemM); medulla.position.set(0, -2.35, -0.75); medulla.rotation.x = 0.4;
    const stemG = new THREE.Group(); stemG.add(cere, pons, medulla); brain.add(stemG);

    // meninges (translucent outer membrane) + skull ghost
    const meningesM = mk({ color: C.meninges, roughness: 0.5, transparent: true, opacity: 0.12, side: THREE.DoubleSide });
    const meninges = new THREE.Mesh(new THREE.SphereGeometry(2.15, 48, 48), meningesM); meninges.scale.set(1.05, 1.0, 1.18);
    const skull = new THREE.Group(); skull.add(meninges); brain.add(skull);

    // ---- vessels ----
    const arteries = new THREE.Group(), veins = new THREE.Group(), caps = new THREE.Group();
    brain.add(arteries, veins, caps);
    const tube = (grp, pts, color, r) => {
      const M = mk({ color, roughness: 0.45, metalness: 0.05 }); orig.set(M, color);
      const cv = new THREE.CatmullRomCurve3(pts.map((x) => new THREE.Vector3(...x)));
      grp.add(new THREE.Mesh(new THREE.TubeGeometry(cv, 44, r, 8), M));
    };
    tube(arteries, [[-1.7, -0.9, 0.9], [-0.6, -0.5, 1.2], [0.5, 0.2, 1.6], [1.4, 0.6, 1.2]], C.artery, 0.045);
    tube(arteries, [[1.7, -0.8, 0.8], [0.8, -0.2, 1.5], [-0.2, 0.4, 1.5], [-1.3, 0.5, 1.0]], C.artery, 0.04);
    tube(arteries, [[0, -1.4, 0.2], [0, -0.5, 0.5], [0, 0.3, 0.7]], C.artery, 0.05);   // basilar-ish
    tube(veins, [[0, 1.7, -1.6], [0, 1.5, -0.2], [0, 1.2, 1.2]], C.vein, 0.05);        // sup. sagittal sinus
    tube(veins, [[-1.5, 0.3, -0.8], [-0.5, -0.1, 0.4], [0.3, -0.4, 0.9]], C.vein, 0.035);

    // capillaries — InstancedMesh of many tiny segments on the cortical surface
    const capCount = 900;
    const capGeo = new THREE.CylinderGeometry(0.006, 0.006, 0.16, 4);
    const capMat = mk({ color: C.capillary, roughness: 0.6 }); orig.set(capMat, C.capillary);
    const capMesh = new THREE.InstancedMesh(capGeo, capMat, capCount);
    const dm = new THREE.Object3D();
    for (let i = 0; i < capCount; i++) {
      const u = Math.random() * Math.PI * 2, w = Math.acos(2 * Math.random() - 1);
      const rr = 1.85 + Math.random() * 0.18;
      const x = rr * Math.sin(w) * Math.cos(u) * 1.15, y = rr * Math.cos(w) * 0.96, z = rr * Math.sin(w) * Math.sin(u) * 1.12;
      dm.position.set(x, y, z); dm.lookAt(x * 1.4, y * 1.4, z * 1.4);
      dm.rotation.z += Math.random(); dm.updateMatrix(); capMesh.setMatrixAt(i, dm.matrix);
    }
    caps.add(capMesh);

    // ---- hemorrhage (illustrative) — deep, slightly left (basal ganglia) ----
    const hemoG = new THREE.Group(); brain.add(hemoG);
    const clotM = mk({ color: C.hemo, roughness: 0.55 }); orig.set(clotM, C.hemo);
    const clot = new THREE.Mesh(new THREE.SphereGeometry(0.44, 32, 32), clotM);
    clot.position.set(-0.55, -0.02, 0.38); hemoG.add(clot);
    const clotCore = new THREE.Mesh(new THREE.SphereGeometry(0.24, 24, 24), mk({ color: C.hemo2, roughness: 0.5 }));
    clotCore.position.copy(clot.position); hemoG.add(clotCore);
    const edemaM = new THREE.MeshStandardMaterial({ color: C.edema, roughness: 0.6, transparent: true, opacity: 0.14 }); mats.push(edemaM);
    const edema = new THREE.Mesh(new THREE.SphereGeometry(0.9, 24, 24), edemaM); edema.position.copy(clot.position); hemoG.add(edema);
    // ruptured vessel stub feeding the clot
    tube(hemoG, [[-1.2, -0.6, 0.9], [-0.8, -0.3, 0.6], [-0.55, -0.02, 0.38]], 0x8a2530, 0.03);

    // ---- slicing: three orthogonal planes on the fixed convention + freeform --
    const planes = {
      sagittal: new THREE.Plane(new THREE.Vector3(1, 0, 0), 3),   // ±X
      coronal:  new THREE.Plane(new THREE.Vector3(0, 0, 1), 3),   // ±Z
      axial:    new THREE.Plane(new THREE.Vector3(0, 1, 0), 3),   // ±Y
      freeform: new THREE.Plane(new THREE.Vector3(1, 1, 0.4).normalize(), 3),
    };
    const enabled = { sagittal: false, coronal: false, axial: false, freeform: false };
    function updateClips() {
      const active = Object.keys(enabled).filter((k) => enabled[k]).map((k) => planes[k]);
      mats.forEach((m) => { m.clippingPlanes = active; m.clipIntersection = false; });
    }

    // ---- imaging re-skins (illustrative rendering styles) ----
    let imaging = "anatomy";
    function setColor(m, c) { if (m && m.color) m.color.setHex(c); }
    function setImaging(mode) {
      imaging = mode;
      // restore anatomical first
      orig.forEach((c, m) => { setColor(m, c); if (m.opacity !== undefined) { /* keep */ } });
      cortex.visible = true; interior.visible = true; caps.visible = true;
      arteries.visible = true; veins.visible = true; skull.visible = false; edema.visible = true;
      if (mode === "mri") { orig.forEach((c, m) => setColor(m, 0x000000)); // grayscale ramp below
        setColor(R.M, 0x9aa0aa); setColor(L.M, 0x9aa0aa); setColor(wmM, 0xe6e6ea);
        deep.children.forEach((n) => setColor(n.material, 0x8b909a)); setColor(clotM, 0xf2f2f4); setColor(clotCore.material, 0xffffff);
      } else if (mode === "ct") { setColor(R.M, C.ct_tissue); setColor(L.M, C.ct_tissue); setColor(wmM, 0x363b42);
        deep.children.forEach((n) => setColor(n.material, 0x30353c)); skull.visible = true; meningesM.opacity = 0.28; setColor(meningesM, C.ct_bone);
        setColor(clotM, C.ct_blood); setColor(clotCore.material, C.ct_blood); caps.visible = false;
      } else if (mode === "vascular") { R.M.opacity = 0.12; L.M.opacity = 0.12; wmM.opacity = 0.1; interior.visible = true;
        deep.children.forEach((n) => n.material.opacity = 0.15); arteries.visible = true; veins.visible = true;
      } else if (mode === "perfusion") { setColor(R.M, 0x3a5f8f); setColor(L.M, 0x3a5f8f); // cool = low near clot, warm elsewhere (illustrative)
        setColor(clotM, 0x101418); caps.visible = false;
      } else { // anatomy
        R.M.opacity = 1; L.M.opacity = 1; wmM.opacity = 0.92; meningesM.opacity = 0.12; setColor(meningesM, C.meninges);
        deep.children.forEach((n) => n.material.opacity = 0.95);
      }
    }

    // ---- layer isolation ----
    const layerMap = {
      "Skull / meninges": [skull], "Arteries & veins": [arteries, veins],
      "Capillaries": [caps], "Cortex & white matter": [cortex, wm, cc],
      "Deep structures & ventricles": [deep, ventL, ventR], "Blood–brain barrier": [caps],
      "Cerebellum & brainstem": [stemG],
    };
    function setLayer(name, on) { (layerMap[name] || []).forEach((o) => (o.visible = on)); }

    // ---- lobe isolation ----
    function isolateLobe(name) {
      const whole = !name || name === "whole brain";
      R.M.opacity = whole ? 1 : 0.14; L.M.opacity = whole ? 1 : 0.14;
      lobes.children.forEach((c) => {
        const hit = !whole && (c.userData.lobe === name || c.userData.lobe === name + "_l");
        c.material.opacity = hit ? 0.5 : 0.0;
      });
    }

    // ---- hemorrhage mode + time (acute -> recovery) ----
    let hemoOn = true;
    function setHemorrhage(on) { hemoOn = on; hemoG.visible = on;
      const shift = on ? 0.06 : 0;                       // subtle mass effect (midline shift)
      ventL.position.x = 0.35 + shift; ventR.position.x = -0.35 + shift; wm.position.x = shift * 0.5;
    }
    function setTime(t) {                                 // t in [0,1] => 0..30 days (illustrative)
      const e = 1.35 - 0.75 * t;                          // edema grows early, resolves late
      edema.scale.setScalar(e); edemaM.opacity = 0.16 * (1 - 0.6 * t);
      const cs = 1.0 - 0.55 * t;                          // clot resorption
      clot.scale.setScalar(cs); clotCore.scale.setScalar(cs);
    }
    setTime(0.15);

    // ---- controls: rotate (drag) · zoom (wheel) · pan (shift/right-drag) ----
    let rx = 0.16, ry = 0.5, down = 0, px = 0, py = 0, auto = true, dragged = false;
    const dom = renderer.domElement;
    dom.addEventListener("pointerdown", (e) => { down = e.shiftKey || e.button === 2 ? 2 : 1; dragged = false; auto = false; px = e.clientX; py = e.clientY; });
    dom.addEventListener("contextmenu", (e) => e.preventDefault());
    window.addEventListener("pointerup", () => (down = 0));
    window.addEventListener("pointermove", (e) => {
      if (!down) return; const dx = e.clientX - px, dy = e.clientY - py;
      if (Math.abs(dx) + Math.abs(dy) > 3) dragged = true;
      if (down === 2) { pivot.position.x += dx * 0.006; pivot.position.y -= dy * 0.006; }
      else { ry += dx * 0.008; rx += dy * 0.008; }
      px = e.clientX; py = e.clientY;
    });
    dom.addEventListener("wheel", (e) => { e.preventDefault(); camera.position.z = Math.max(3.5, Math.min(13, camera.position.z + e.deltaY * 0.01)); }, { passive: false });

    // click a tagged structure -> label callback (approximate anatomy)
    const pickables = [
      { root: R.lod, label: "Cerebral cortex (right)" }, { root: L.lod, label: "Cerebral cortex (left)" },
      { root: wm, label: "White matter" }, { root: cc, label: "Corpus callosum" },
      { root: ventL, label: "Lateral ventricle (left)" }, { root: ventR, label: "Lateral ventricle (right)" },
      { root: cere, label: "Cerebellum" }, { root: pons, label: "Pons" }, { root: medulla, label: "Medulla" },
      { root: clot, label: "Hemorrhage (illustrative)" },
    ];
    deep.children.forEach((n) => pickables.push({ root: n, label: (n.userData.region || "deep nucleus") + " (approx.)" }));
    dom.addEventListener("click", (e) => {
      if (dragged || !opts.onPick) return;
      const rect = dom.getBoundingClientRect();
      const m = new THREE.Vector2(((e.clientX - rect.left) / rect.width) * 2 - 1, -((e.clientY - rect.top) / rect.height) * 2 + 1);
      const ray = new THREE.Raycaster(); ray.setFromCamera(m, camera);
      const hits = ray.intersectObjects(pickables.map((p) => p.root), true);
      if (!hits.length) return;
      let o = hits[0].object, pick = null;
      while (o && !pick) { pick = pickables.find((p) => p.root === o); o = o.parent; }
      if (pick) opts.onPick({ name: pick.label, x: e.clientX, y: e.clientY, isHemorrhage: pick.root === clot });
    });

    setImaging("anatomy");
    let alive = true, t = 0;
    (function loop() {
      if (!alive || !host.isConnected) { alive = false; renderer.dispose(); return; }
      requestAnimationFrame(loop); t += 0.016; if (auto) ry += 0.0018;
      brain.rotation.y = ry; brain.rotation.x = rx;
      R.lod.update(camera); L.lod.update(camera);
      renderer.render(scene, camera);
    })();
    window.addEventListener("resize", () => { const w = host.clientWidth, h = host.clientHeight || 520; camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h); });

    return {
      setLayer, isolateLobe, setImaging, setHemorrhage, setTime,
      setSlice(axis, on, value) { if (!(axis in enabled)) return; enabled[axis] = on;
        if (value !== undefined) planes[axis].constant = -value; updateClips(); },
      setView(preset) {                          // known anatomical orientations
        auto = false;
        if (preset === "anterior") { rx = 0; ry = 0; }
        else if (preset === "lateral") { rx = 0; ry = Math.PI / 2; }
        else if (preset === "superior") { rx = -Math.PI / 2 + 0.001; ry = 0; }
        else { rx = 0.16; ry = 0.5; pivot.position.set(0, 0, 0); }   // reset
        camera.position.z = 10.2;
      },
      setAutoRotate(on) { auto = !!on; },
      dispose() { alive = false; try { renderer.dispose(); } catch (e) {} host.innerHTML = ""; },
    };
  }

  /* ---------------- Cellular Environment (macro->micro perivascular niche) ----
     Illustrative schematic of ESTABLISHED cell biology. Instanced meshes for the
     numerous cell types (RBCs, endothelium, microglia, immune cells). */
  function initCellScene(host, opts) {
    opts = opts || {};
    if (!OK || !webglOK()) return fallback(host, "Illustrative Cellular Environment");
    const W = host.clientWidth, H = host.clientHeight || 420;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(48, W / H, 0.1, 100); camera.position.set(0, 0.5, 7);
    let renderer; try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
    catch (e) { return fallback(host, "Illustrative Cellular Environment"); }
    renderer.setSize(W, H); renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1)); host.appendChild(renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xf4efe6, 0x1b1c20, 0.7));
    const key = new THREE.DirectionalLight(0xffffff, 0.7); key.position.set(3, 4, 5); scene.add(key);
    const g = new THREE.Group(); scene.add(g);

    // capillary (a translucent tube across the scene) + endothelial lining + pericytes
    const capMat = new THREE.MeshStandardMaterial({ color: 0xb98f95, roughness: 0.5, transparent: true, opacity: 0.35, side: THREE.DoubleSide });
    const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 8, 32, 1, true), capMat); cap.rotation.z = Math.PI / 2; g.add(cap);
    const groups = {};   // cell-type -> Object3D for highlight
    const endoGeo = new THREE.BoxGeometry(0.5, 0.28, 0.9), endoMat = new THREE.MeshStandardMaterial({ color: 0x8fb0c8, roughness: 0.5 });
    const endo = new THREE.InstancedMesh(endoGeo, endoMat, 60), o = new THREE.Object3D();
    for (let i = 0; i < 60; i++) { const a = (i / 60) * Math.PI * 2, x = (i % 15 - 7) * 0.55;
      o.position.set(x, Math.cos(a) * 0.92, Math.sin(a) * 0.92); o.lookAt(x, 0, 0); o.updateMatrix(); endo.setMatrixAt(i, o.matrix); }
    g.add(endo); groups.endothelial = endo;

    // red blood cells INSIDE the vessel (instanced biconcave-ish discs)
    const rbcMat = new THREE.MeshStandardMaterial({ color: 0xa5202e, roughness: 0.4 });
    const rbc = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.28, 0.28, 0.12, 16), rbcMat, 40);
    const rbcData = [];
    for (let i = 0; i < 40; i++) { const p = { x: -4 + Math.random() * 8, y: (Math.random() - 0.5) * 1.2, z: (Math.random() - 0.5) * 1.2, s: 0.8 + Math.random() * 0.4 };
      rbcData.push(p); o.position.set(p.x, p.y, p.z); o.rotation.set(Math.random(), Math.random(), Math.PI / 2); o.scale.setScalar(p.s); o.updateMatrix(); rbc.setMatrixAt(i, o.matrix); }
    g.add(rbc); groups["red blood cell"] = rbc;

    // platelets (small, near a rupture) + immune cells (instanced)
    const platMat = new THREE.MeshStandardMaterial({ color: 0xe0c07a, roughness: 0.5 });
    const plat = new THREE.InstancedMesh(new THREE.SphereGeometry(0.11, 8, 8), platMat, 24);
    for (let i = 0; i < 24; i++) { o.position.set(1 + Math.random() * 1.6, (Math.random() - 0.5) * 1.6, (Math.random() - 0.5) * 1.6); o.scale.setScalar(1); o.updateMatrix(); plat.setMatrixAt(i, o.matrix); }
    g.add(plat); groups.platelet = plat;
    const immMat = new THREE.MeshStandardMaterial({ color: 0x9c6fb0, roughness: 0.6 });
    const imm = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.22, 1), immMat, 14);
    for (let i = 0; i < 14; i++) { o.position.set(-3 + Math.random() * 6, 1.2 + Math.random() * 1.4, (Math.random() - 0.5) * 2); o.scale.setScalar(1); o.updateMatrix(); imm.setMatrixAt(i, o.matrix); }
    g.add(imm); groups["immune cell"] = imm;

    // pericytes hugging the vessel
    const periMat = new THREE.MeshStandardMaterial({ color: 0xb58fa0, roughness: 0.6 });
    const peri = new THREE.InstancedMesh(new THREE.SphereGeometry(0.18, 12, 12), periMat, 20);
    for (let i = 0; i < 20; i++) { const x = -3.5 + i * 0.37; o.position.set(x, Math.cos(i) * 1.0, Math.sin(i) * 1.0); o.scale.set(1.6, 0.8, 0.8); o.updateMatrix(); peri.setMatrixAt(i, o.matrix); }
    g.add(peri); groups.pericyte = peri;

    // astrocytes with end-feet contacting the vessel (star shapes)
    const astro = new THREE.Group();
    for (let k = 0; k < 4; k++) { const cx = -3 + k * 2, cy = 1.8, cz = (k % 2 ? 1 : -1) * 0.8;
      const soma = new THREE.Mesh(new THREE.IcosahedronGeometry(0.24, 1), new THREE.MeshStandardMaterial({ color: 0x8fbf9e, roughness: 0.6 }));
      soma.position.set(cx, cy, cz); astro.add(soma);
      for (let f = 0; f < 6; f++) { const a = (f / 6) * Math.PI * 2; const end = new THREE.Vector3(cx + Math.cos(a) * 0.6, cy - 0.9, cz + Math.sin(a) * 0.6);
        const cvv = new THREE.CatmullRomCurve3([new THREE.Vector3(cx, cy, cz), end]);
        astro.add(new THREE.Mesh(new THREE.TubeGeometry(cvv, 6, 0.03, 5), new THREE.MeshStandardMaterial({ color: 0x8fbf9e, roughness: 0.6 }))); } }
    g.add(astro); groups.astrocyte = astro;

    // neurons (soma + dendrites + axon)
    const neu = new THREE.Group();
    for (let k = 0; k < 3; k++) { const cx = -2.5 + k * 2.4, cy = -1.9, cz = (k - 1) * 0.9;
      const soma = new THREE.Mesh(new THREE.SphereGeometry(0.3, 20, 20), new THREE.MeshStandardMaterial({ color: 0xcaa27f, roughness: 0.6, emissive: 0x3a2a1a, emissiveIntensity: 0.2 }));
      soma.position.set(cx, cy, cz); neu.add(soma); soma.userData.pulse = true;
      for (let d = 0; d < 5; d++) { const a = (d / 5) * Math.PI * 2; const end = new THREE.Vector3(cx + Math.cos(a) * 0.9, cy + Math.sin(a) * 0.7 + 0.2, cz + Math.cos(a) * 0.3);
        neu.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(cx, cy, cz), end]), 6, 0.025, 5), new THREE.MeshStandardMaterial({ color: 0xcaa27f, roughness: 0.6 }))); }
      neu.add(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3([new THREE.Vector3(cx, cy, cz), new THREE.Vector3(cx + 1.6, cy - 0.2, cz)]), 8, 0.03, 5), new THREE.MeshStandardMaterial({ color: 0xd8c0a0, roughness: 0.6 }))); }
    g.add(neu); groups.neuron = neu;

    // microglia (activated, amoeboid) — instanced displaced blobs
    const micMat = new THREE.MeshStandardMaterial({ color: 0xd9a441, roughness: 0.7 });
    const mic = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.26, 1), micMat, 10);
    for (let i = 0; i < 10; i++) { o.position.set(-3 + Math.random() * 6, -0.5 + Math.random() * 2.5, (Math.random() - 0.5) * 2.5); o.rotation.set(Math.random(), Math.random(), 0); o.scale.setScalar(0.9 + Math.random() * 0.5); o.updateMatrix(); mic.setMatrixAt(i, o.matrix); }
    g.add(mic); groups.microglia = mic;

    // oligodendrocytes (small, near axons)
    const oli = new THREE.InstancedMesh(new THREE.SphereGeometry(0.15, 10, 10), new THREE.MeshStandardMaterial({ color: 0xa9b0c8, roughness: 0.6 }), 8);
    for (let i = 0; i < 8; i++) { o.position.set(-2 + Math.random() * 4, -1.2 + Math.random() * 0.8, (Math.random() - 0.5) * 1.5); o.scale.setScalar(1); o.updateMatrix(); oli.setMatrixAt(i, o.matrix); }
    g.add(oli); groups.oligodendrocyte = oli;

    let rx = 0.1, ry = 0.2, down = false, px = 0, py = 0, auto = true, dragged = false;
    const dom = renderer.domElement;
    dom.addEventListener("pointerdown", (e) => { down = true; dragged = false; auto = false; px = e.clientX; py = e.clientY; });
    window.addEventListener("pointerup", () => (down = false));
    window.addEventListener("pointermove", (e) => { if (!down) return; const dx = e.clientX - px, dy = e.clientY - py; if (Math.abs(dx) + Math.abs(dy) > 3) dragged = true; ry += dx * 0.008; rx += dy * 0.008; px = e.clientX; py = e.clientY; });
    dom.addEventListener("wheel", (e) => { e.preventDefault(); camera.position.z = Math.max(3, Math.min(14, camera.position.z + e.deltaY * 0.01)); }, { passive: false });

    let flow = 0.5, activity = 0.5;
    let alive = true, t = 0;
    (function loop() {
      if (!alive || !host.isConnected) { alive = false; renderer.dispose(); return; }
      requestAnimationFrame(loop); t += 0.016; if (auto) ry += 0.0015; g.rotation.y = ry; g.rotation.x = rx;
      // RBC flow along the vessel
      for (let i = 0; i < rbcData.length; i++) { const p = rbcData[i]; p.x += 0.02 + flow * 0.05; if (p.x > 4) p.x = -4;
        o.position.set(p.x, p.y, p.z); o.rotation.set(p.x, p.z, Math.PI / 2); o.scale.setScalar(p.s); o.updateMatrix(); rbc.setMatrixAt(i, o.matrix); }
      rbc.instanceMatrix.needsUpdate = true;
      neu.children.forEach((m) => { if (m.userData.pulse) m.material.emissiveIntensity = 0.15 + activity * 0.4 * (0.5 + 0.5 * Math.sin(t * 3)); });
      renderer.render(scene, camera);
    })();
    window.addEventListener("resize", () => { const w = host.clientWidth, h = host.clientHeight || 420; camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h); });

    return {
      highlight(type) { Object.keys(groups).forEach((k) => { const obj = groups[k]; const on = k === type;
        obj.traverse ? obj.traverse((m) => { if (m.material) m.material.emissiveIntensity = on ? 0.5 : (m.userData.pulse ? m.material.emissiveIntensity : 0); }) : 0;
        if (obj.material) obj.material.emissive && obj.material.emissive.setHex(on ? 0x333311 : 0x000000); }); },
      setFlow(v) { flow = v; }, setActivity(v) { activity = v; },
      dispose() { alive = false; try { renderer.dispose(); } catch (e) {} host.innerHTML = ""; },
    };
  }

  window.Neuro3D = { initTwin, initCellScene };
})();
