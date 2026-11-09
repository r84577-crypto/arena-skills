"use client";

/**
 * مشهد الشبكة السيادية — Three.js.
 *
 * عقد نابضة + حقل جسيمات + اختلاف زاوية مع الفأرة + دوران بطيء.
 * قرارات مقصودة:
 *   - يُستورد ديناميكياً بـ ssr:false، فلا يوجد HTML من الخادم لمشهد لا يُرى.
 *   - يُنظّف كل مورد عند الإزالة، وإلا تسرّب الذاكرة.
 *   - يحترم prefers-reduced-motion: إطار واحد ساكن.
 *   - devicePixelRatio مقيّد بـ 2، لأن الشاشات 4K تحرق GPU بلا فائدة بصرية.
 */

import { useEffect, useRef } from "react";
import type * as THREE_TYPES from "three";

type Node = { pos: [number, number, number]; size: number; color: number };

const NODES: Node[] = [
  { pos: [0, 0, 0], size: 0.36, color: 0x4ea8de }, // المركز: المالك
  { pos: [1.9, 0.9, -0.4], size: 0.2, color: 0x3fb27f }, // الصحة
  { pos: [-1.8, 1.1, 0.5], size: 0.2, color: 0xd9a441 }, // المال
  { pos: [1.6, -1.2, 0.6], size: 0.2, color: 0x8b98ad }, // الذاكرة
  { pos: [-1.7, -1.0, -0.6], size: 0.2, color: 0x4ea8de }, // العمل
  { pos: [0.2, 1.9, 0.8], size: 0.16, color: 0xd95d5d }, // القيود
];

const EDGES: [number, number][] = [
  [0, 1], [0, 2], [0, 3], [0, 4], [0, 5],
  [1, 3], [2, 4], [3, 5],
];

const PARTICLES = 320;

export default function SovereignScene() {
  const hostRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    let disposed = false;
    let cleanup = () => {};

    (async () => {
      const THREE = await import("three");
      if (disposed || !host) return;

      const width = host.clientWidth || 800;
      const height = host.clientHeight || 380;

      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(width, height, false);
      host.appendChild(renderer.domElement);

      const scene = new THREE.Scene();
      const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
      camera.position.set(0, 0.6, 6.4);
      camera.lookAt(0, 0, 0);

      const group = new THREE.Group();
      scene.add(group);

      const geoms: THREE_TYPES.BufferGeometry[] = [];
      const mats: THREE_TYPES.Material[] = [];

      // عُقد نابضة
      const meshes: THREE_TYPES.Mesh[] = [];
      const baseSizes = NODES.map((n) => n.size);
      NODES.forEach((n) => {
        const g = new THREE.SphereGeometry(n.size, 32, 32);
        const m = new THREE.MeshStandardMaterial({
          color: n.color,
          emissive: n.color,
          emissiveIntensity: 0.5,
          roughness: 0.32,
          metalness: 0.3,
        });
        const mesh = new THREE.Mesh(g, m);
        mesh.position.set(...n.pos);
        group.add(mesh);
        meshes.push(mesh);
        geoms.push(g);
        mats.push(m);
      });

      // وصلات
      const edgeMats: THREE_TYPES.LineBasicMaterial[] = [];
      EDGES.forEach(([a, b]) => {
        const g = new THREE.BufferGeometry().setFromPoints([
          new THREE.Vector3(...NODES[a].pos),
          new THREE.Vector3(...NODES[b].pos),
        ]);
        const m = new THREE.LineBasicMaterial({ color: 0x2b3a52, transparent: true, opacity: 0.85 });
        group.add(new THREE.Line(g, m));
        geoms.push(g);
        mats.push(m);
        edgeMats.push(m);
      });

      // حقل جسيمات
      const pGeo = new THREE.BufferGeometry();
      const positions = new Float32Array(PARTICLES * 3);
      for (let i = 0; i < PARTICLES; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 12;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 7;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 8 - 2;
      }
      pGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      const pMat = new THREE.PointsMaterial({
        color: 0x4ea8de,
        size: 0.035,
        transparent: true,
        opacity: 0.55,
        sizeAttenuation: true,
      });
      const particles = new THREE.Points(pGeo, pMat);
      scene.add(particles);
      geoms.push(pGeo);
      mats.push(pMat);

      // إضاءة
      const key = new THREE.DirectionalLight(0xffffff, 1.15);
      key.position.set(3, 4, 5);
      scene.add(key);
      const rim = new THREE.PointLight(0x4ea8de, 12, 20);
      rim.position.set(-3, -2, 3);
      scene.add(rim);
      scene.add(new THREE.AmbientLight(0x2a3550, 1.1));

      const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      // اختلاف الزاوية مع الفأرة
      let targetX = 0;
      let targetY = 0.6;
      const onPointer = (e: PointerEvent) => {
        const r = host.getBoundingClientRect();
        const nx = ((e.clientX - r.left) / r.width - 0.5) * 2;
        const ny = ((e.clientY - r.top) / r.height - 0.5) * 2;
        targetX = nx * 0.9;
        targetY = 0.6 - ny * 0.55;
      };
      if (!reduce) host.addEventListener("pointermove", onPointer);

      let raf = 0;
      const clockStart = performance.now();

      const render = () => {
        if (disposed) return;
        if (!reduce) raf = requestAnimationFrame(render);

        const t = (performance.now() - clockStart) / 1000;

        if (!reduce) {
          group.rotation.y = t * 0.16;
          group.rotation.x = Math.sin(t * 0.28) * 0.07;
          // نبض العقد
          meshes.forEach((mesh, i) => {
            const s = 1 + Math.sin(t * 1.7 + i * 1.1) * 0.07;
            mesh.scale.setScalar(s);
            void baseSizes[i];
          });
          // تنفّس الوصلات
          edgeMats.forEach((m, i) => {
            m.opacity = 0.6 + Math.sin(t * 1.2 + i * 0.7) * 0.25;
          });
          // انجراف الجسيمات
          particles.rotation.y = t * 0.02;
          // لحاق الكاميرا بالفأرة
          camera.position.x += (targetX - camera.position.x) * 0.04;
          camera.position.y += (targetY - camera.position.y) * 0.04;
          camera.lookAt(0, 0, 0);
        }

        renderer.render(scene, camera);
      };
      render();

      const onResize = () => {
        const w = host.clientWidth || width;
        const h = host.clientHeight || height;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      };
      const ro = new ResizeObserver(onResize);
      ro.observe(host);

      cleanup = () => {
        cancelAnimationFrame(raf);
        ro.disconnect();
        host.removeEventListener("pointermove", onPointer);
        geoms.forEach((g) => g.dispose());
        mats.forEach((m) => m.dispose());
        renderer.dispose();
        if (renderer.domElement.parentElement === host) {
          host.removeChild(renderer.domElement);
        }
      };
    })();

    return () => {
      disposed = true;
      cleanup();
    };
  }, []);

  return (
    <div ref={hostRef} className="scene-shell enter" aria-hidden="true">
      <span className="scene-caption">الشبكة السيادية — المالك في المركز</span>
    </div>
  );
}
