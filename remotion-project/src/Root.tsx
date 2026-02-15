import { Composition } from "remotion";
import { Video } from "./Video";
import { VideoITAI } from "./VideoITAI";

// 既存の動画用タイミングデータ
let timingsData: any;
try {
  timingsData = require("../timings.json");
} catch (error) {
  timingsData = { fps: 30, totalFrames: 150, slides: [] };
}

// IT・AI教育動画用タイミングデータ
let timingsITAI: any;
try {
  timingsITAI = require("../timings_it_ai.json");
} catch (error) {
  timingsITAI = { fps: 30, totalFrames: 150, slides: [] };
}

export const RemotionRoot = () => {
  return (
    <>
      {/* 既存の動画 */}
      <Composition
        id="Video"
        component={Video}
        durationInFrames={timingsData.totalFrames || 150}
        fps={timingsData.fps || 30}
        width={1920}
        height={1080}
        defaultProps={{
          slides: timingsData.slides || [],
          fps: timingsData.fps || 30,
          totalFrames: timingsData.totalFrames || 150,
        }}
      />

      {/* IT・AI教育動画 */}
      <Composition
        id="VideoITAI"
        component={VideoITAI}
        durationInFrames={timingsITAI.totalFrames || 150}
        fps={timingsITAI.fps || 30}
        width={1920}
        height={1080}
        defaultProps={{
          slides: timingsITAI.slides || [],
        }}
      />
    </>
  );
};
