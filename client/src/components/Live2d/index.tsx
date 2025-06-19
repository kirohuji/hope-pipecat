import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import * as PIXI from "pixi.js";
import { Live2DModel } from "pixi-live2d-display";

// 声明 window.PIXI 类型
declare global {
  interface Window {
    PIXI: typeof PIXI;
  }
}
window.PIXI = PIXI;

export interface PixiCanvasRef {
  triggerMotion: (motionName: string) => void;
}

const PixiCanvas = forwardRef<PixiCanvasRef>((_props, ref) => {
  const canvasRef = useRef(null);
  const modelRef = useRef<Live2DModel | null>(null);

  useImperativeHandle(ref, () => ({
    triggerMotion: (motionName: string) => {
      if (modelRef.current) {
        console.log("手动触发动作:", motionName);
        // // 先停止当前动作
        // modelRef.current.motion('Idle');
        // 然后触发新动作
        modelRef.current.motion(motionName);
      }
    },
  }));

  useEffect(() => {
    const canvas = document.getElementById(
      "live2d",
    ) as HTMLCanvasElement | null;
    if (!canvas) return;
    const app = new PIXI.Application({
      view: canvas,
      autoStart: true,
      resizeTo: window,
      backgroundAlpha: 0,
    });

    async function loadModel() {
      console.log("开始加载模型...");
      const model = await Live2DModel.from(
        "/character/wanko/runtime/wanko_touch.model3.json",
      );
      console.log("模型加载完成");
      // 保存 model 实例
      modelRef.current = model;
      // 缩放模型
      model.scale.set(0.5, 0.5);
      model.x = -130;
      app.stage.addChild(model);
      console.log("模型已添加到舞台");
      model.on("hit", (hitAreas) => {
        console.log("触发点击事件", hitAreas);
        if (hitAreas.includes("body")) {
          console.log("执行 Shake 动作");
          model.motion("Shake");
        }
      });
    }

    loadModel();
  }, []);

  return (
    <div style={{ position: "relative", background: "#fff", height: "100%" }}>
      <canvas
        ref={canvasRef}
        id="live2d"
        style={{ width: "100%", height: "100%", background: "#fff" }}
      />
    </div>
  );
});

export default PixiCanvas;
