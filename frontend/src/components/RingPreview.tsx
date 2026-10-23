import { useEffect, useRef } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { toBufferData } from "../mesh";
import { orthoFrustum } from "../trueScale";
import type { MeshData } from "../types";

export type ViewMode = "inspect" | "life-size";

interface Props {
  mesh: MeshData | null;
  metal: string;
  mode: ViewMode;
  pxPerMm: number;
}

const COLORS: Record<string, number> = { silver_925: 0xdfe3e8, gold_14k: 0xd9b45a, gold_18k: 0xe6b84a };

/** The ring axis is Z and the head points +Y. Inspect mode orbits in perspective; life-size mode
 *  looks straight down the ring axis with an orthographic camera at an exact pixels-per-mm scale. */
export function RingPreview({ mesh, metal, mode, pxPerMm }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const three = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    persp: THREE.PerspectiveCamera;
    ortho: THREE.OrthographicCamera;
    controls: OrbitControls;
    material: THREE.MeshPhysicalMaterial;
    object: THREE.Mesh | null;
    framed: boolean;
    size: { w: number; h: number };
  } | null>(null);
  const live = useRef({ mode, pxPerMm });
  live.current = { mode, pxPerMm };

  // Set up the scene once.
  useEffect(() => {
    const el = host.current!;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    el.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const pmrem = new THREE.PMREMGenerator(renderer);
    scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    const key = new THREE.DirectionalLight(0xffffff, 1.2);
    key.position.set(20, 30, 40);
    scene.add(key);

    const persp = new THREE.PerspectiveCamera(35, 1, 1, 500);
    const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 1000);
    const controls = new OrbitControls(persp, renderer.domElement);
    controls.enableDamping = true;
    const material = new THREE.MeshPhysicalMaterial({ color: COLORS.silver_925, metalness: 1, roughness: 0.25 });

    const state = { renderer, scene, persp, ortho, controls, material, object: null as THREE.Mesh | null,
      framed: false, size: { w: 1, h: 1 } };
    three.current = state;

    const applySize = () => {
      const w = Math.max(1, el.clientWidth);
      const h = Math.max(1, el.clientHeight);
      state.size = { w, h };
      renderer.setSize(w, h, false);
      persp.aspect = w / h;
      persp.updateProjectionMatrix();
      Object.assign(ortho, orthoFrustum(w, h, live.current.pxPerMm));
      ortho.updateProjectionMatrix();
    };
    applySize();
    const observer = new ResizeObserver(applySize);
    observer.observe(el);

    let frame = 0;
    const loop = () => {
      frame = requestAnimationFrame(loop);
      controls.update();
      renderer.render(scene, live.current.mode === "life-size" ? ortho : persp);
    };
    loop();

    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      state.object?.geometry.dispose();
      material.dispose();
      pmrem.dispose();
      renderer.dispose();
      renderer.domElement.remove();
      three.current = null;
    };
  }, []);

  // Replace the geometry when the server sends a new mesh.
  useEffect(() => {
    const t = three.current;
    if (!t) return;
    if (t.object) {
      t.scene.remove(t.object);
      t.object.geometry.dispose();
      t.object = null;
    }
    if (!mesh) return;
    const { positions, indices } = toBufferData(mesh);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setIndex(new THREE.BufferAttribute(indices, 1));
    geometry.computeVertexNormals();
    geometry.computeBoundingSphere();
    t.object = new THREE.Mesh(geometry, t.material);
    t.scene.add(t.object);

    const { center, radius } = geometry.boundingSphere!;
    t.ortho.position.set(center.x, center.y, 100);
    t.ortho.lookAt(center.x, center.y, 0);
    if (!t.framed) {
      t.persp.position.set(center.x + radius * 1.5, center.y + radius * 1.1, center.z + radius * 3);
      t.controls.target.copy(center);
      t.controls.update();
      t.framed = true;
    }
  }, [mesh]);

  useEffect(() => {
    three.current?.material.color.setHex(COLORS[metal] ?? COLORS.silver_925);
  }, [metal]);

  // Keep exactly pxPerMm pixels per millimetre in life-size mode.
  useEffect(() => {
    const t = three.current;
    if (!t) return;
    Object.assign(t.ortho, orthoFrustum(t.size.w, t.size.h, pxPerMm));
    t.ortho.updateProjectionMatrix();
  }, [pxPerMm, mode]);

  return <div className="preview" ref={host} role="img" aria-label="3D preview of the ring" />;
}
