import { useCurrentFrame, Img, Audio, useVideoConfig, staticFile, Sequence, spring, interpolate } from "remotion";
import "./fonts.css";

const idleImages = [
  staticFile("idle1.png"),
  staticFile("idle2.png"),
  staticFile("idle3.png"),
  staticFile("idle4.png"),
  staticFile("idle5.png"),
  staticFile("idle6.png"),
];

const talkImages = [
  staticFile("talk1.png"),
  staticFile("talk2.png"),
  staticFile("talk3.png"),
  staticFile("talk4.png"),
  staticFile("talk5.png"),
  staticFile("talk6.png"),
];

interface Subtitle {
  text: string;
  start: number;
  end: number;
  startFrame: number;
  endFrame: number;
}

interface SlideData {
  index: number;
  slideIndex: number;
  audioFile: string;
  audioFiles?: string[];
  durationFrames: number;
  startFrame: number;
  endFrame: number;
  subtitles: Subtitle[];
}

interface VideoProps {
  slides: SlideData[];
  fps: number;
  totalFrames: number;
}

export const Video: React.FC<VideoProps> = ({ slides, fps, totalFrames }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  // 現在のスライドを見つける
  const currentSlide = slides.find(
    (slide) => frame >= slide.startFrame && frame < slide.endFrame
  );

  // 現在の字幕を見つける
  const currentSubtitle = currentSlide?.subtitles.find(
    (subtitle) => frame >= subtitle.startFrame && frame < subtitle.endFrame
  );

  // 音声が再生中かどうかを判定
  let isTalking = false;
  if (currentSubtitle) {
    const subtitleDurationFrames = currentSubtitle.endFrame - currentSubtitle.startFrame;
    const frameInSubtitle = frame - currentSubtitle.startFrame;
    const pauseFrames = 3;
    if (subtitleDurationFrames <= pauseFrames * 2) {
      isTalking = true;
    } else {
      isTalking = frameInSubtitle >= pauseFrames && frameInSubtitle < subtitleDurationFrames - pauseFrames;
    }
  }

  // 使用する画像配列を選択
  const images = isTalking ? talkImages : idleImages;
  const animationSpeed = isTalking ? 3 : 5;
  const imageIndex = Math.floor(frame / animationSpeed) % images.length;
  const imageToShow = images[imageIndex];

  // 現在のスライド画像
  const currentSlideImage = currentSlide
    ? staticFile(`slides/slide-${String(currentSlide.slideIndex).padStart(2, '0')}.png`)
    : null;

  // スライドアニメーション
  const framesIntoSlide = frame - (currentSlide?.startFrame || 0);
  const slideProgress = spring({
    frame: framesIntoSlide,
    fps,
    config: {
      damping: 100,
      stiffness: 200,
      mass: 0.5,
    },
  });

  const opacity = interpolate(slideProgress, [0, 1], [0, 1]);
  const translateY = interpolate(slideProgress, [0, 1], [20, 0]);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        backgroundColor: "#2d2d2d",
      }}
    >
      {/* 背景画像 */}
      <Img
        src={staticFile("background.png")}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
          zIndex: 0,
        }}
      />

      {/* スライド画像 */}
      {currentSlideImage && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            opacity,
            transform: `translateY(${translateY}px)`,
            zIndex: 1,
          }}
        >
          <Img
            src={currentSlideImage}
            style={{
              maxWidth: "95%",
              maxHeight: "95%",
              objectFit: "contain",
            }}
          />
        </div>
      )}

      {/* キャラクター */}
      <div
        style={{
          position: "absolute",
          bottom: 120,
          right: 80,
          width: "300px",
          height: "300px",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 3,
        }}
      >
        <Img src={imageToShow} style={{ height: "100%" }} />
      </div>

      {/* 字幕 */}
      {currentSubtitle && (
        <div
          style={{
            position: "absolute",
            bottom: 80,
            left: 0,
            right: 0,
            textAlign: "center",
            padding: "0 60px",
            zIndex: 4,
          }}
        >
          <div
            style={{
              color: "white",
              fontSize: 48,
              lineHeight: 1.4,
              fontWeight: 800,
              textShadow: "3px 3px 6px rgba(0,0,0,0.95), -1px -1px 3px rgba(0,0,0,0.95), 1px -1px 3px rgba(0,0,0,0.95), -1px 1px 3px rgba(0,0,0,0.95)",
              fontFamily: "'M PLUS 2', 'Noto Sans JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'Yu Gothic', 'Meiryo', sans-serif",
              maxWidth: "85%",
              margin: "0 auto",
            }}
          >
            {currentSubtitle.text}
          </div>
        </div>
      )}

      {/* 音声 */}
      {slides.map((slide) => (
        <Sequence
          key={slide.index}
          from={slide.startFrame}
          durationInFrames={slide.durationFrames}
        >
          <Audio src={staticFile(slide.audioFile)} />
        </Sequence>
      ))}
    </div>
  );
};
