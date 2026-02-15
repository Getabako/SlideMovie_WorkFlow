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

// レイアウト定数（背景画像に合わせた座標）
const LAYOUT = {
  // スライド領域（16:9）
  slide: {
    x: 10,
    y: 100, // さらに15px下に移動
    width: 1395,
    height: 785, // 1395 * 9 / 16 = 784.6875
  },
  // タイトルスクロール領域（スライドの上）
  titleScroll: {
    x: 10,
    y: 5,
    width: 1395,
    height: 75, // 高さを増やして目立たせる
  },
  // 字幕領域（グレーの四角内）
  subtitle: {
    x: 40,
    y: 910,
    width: 1355,
    height: 155,
    padding: 20,
  },
  // キャラクター位置（右下、下半身見切れ）
  character: {
    right: -155, // さらに右に75px移動
    bottom: -200, // 下半身を画面外に
    height: 900, // 1.5倍大きく
  },
};

interface Subtitle {
  text: string;
  start: number;
  end: number;
  startFrame: number;
  endFrame: number;
}

interface SlideData {
  index: number;
  slideIndex?: number;
  audioFile: string;
  audioFiles?: string[];
  durationFrames: number;
  startFrame: number;
  endFrame: number;
  subtitles: Subtitle[];
  title?: string; // スライドタイトル（オプション）
}

interface VideoProps {
  slides: SlideData[];
  fps: number;
  totalFrames: number;
}

// タイトルスクロールコンポーネント
const TitleScroller: React.FC<{ title: string; frame: number }> = ({ title, frame }) => {
  // 無限スクロールのためのアニメーション
  const scrollSpeed = 2; // ピクセル/フレーム
  const textWidth = title.length * 40; // おおよそのテキスト幅
  const totalWidth = LAYOUT.titleScroll.width + textWidth;

  // 2つのテキストを表示して無限ループを実現
  const offset = (frame * scrollSpeed) % totalWidth;

  return (
    <div
      style={{
        position: "absolute",
        left: LAYOUT.titleScroll.x,
        top: LAYOUT.titleScroll.y,
        width: LAYOUT.titleScroll.width,
        height: LAYOUT.titleScroll.height,
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
      }}
    >
      <div
        style={{
          display: "flex",
          whiteSpace: "nowrap",
          transform: `translateX(${LAYOUT.titleScroll.width - offset}px)`,
        }}
      >
        <span
          style={{
            color: "#00ff00",
            fontSize: 36,
            fontWeight: 900,
            fontFamily: "'M PLUS 2', 'Noto Sans JP', sans-serif",
            marginRight: 1500,
            textShadow: "0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00, 0 0 40px #00aa00",
            letterSpacing: "2px",
          }}
        >
          {title}
        </span>
        <span
          style={{
            color: "#00ff00",
            fontSize: 36,
            fontWeight: 900,
            fontFamily: "'M PLUS 2', 'Noto Sans JP', sans-serif",
            marginRight: 1500,
            textShadow: "0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00, 0 0 40px #00aa00",
            letterSpacing: "2px",
          }}
        >
          {title}
        </span>
        <span
          style={{
            color: "#00ff00",
            fontSize: 36,
            fontWeight: 900,
            fontFamily: "'M PLUS 2', 'Noto Sans JP', sans-serif",
            marginRight: 1500,
            textShadow: "0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00, 0 0 40px #00aa00",
            letterSpacing: "2px",
          }}
        >
          {title}
        </span>
      </div>
    </div>
  );
};

// RPG風字幕コンポーネント
const RPGSubtitle: React.FC<{ text: string }> = ({ text }) => {
  return (
    <div
      style={{
        position: "absolute",
        left: LAYOUT.subtitle.x,
        top: LAYOUT.subtitle.y,
        width: LAYOUT.subtitle.width,
        height: LAYOUT.subtitle.height,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: `${LAYOUT.subtitle.padding}px ${LAYOUT.subtitle.padding + 20}px`,
        boxSizing: "border-box",
        zIndex: 4,
      }}
    >
      <div
        style={{
          color: "white",
          fontSize: 32,
          lineHeight: 1.6,
          fontWeight: 700,
          fontFamily: "'M PLUS 2', 'Noto Sans JP', 'Hiragino Sans', sans-serif",
          textShadow: "2px 2px 4px rgba(0,0,0,0.8), -1px -1px 2px rgba(0,0,0,0.8)",
          maxWidth: "100%",
          textAlign: "center",
          wordBreak: "break-all",
          overflow: "visible",
        }}
      >
        {text}
      </div>
    </div>
  );
};

// スライドタイトルを字幕から推測する関数
const extractTitleFromSubtitles = (subtitles: Subtitle[]): string => {
  if (!subtitles || subtitles.length === 0) return "講座";
  // 最初の字幕の最初の句読点までをタイトルとして使用
  const firstText = subtitles[0].text;
  const match = firstText.match(/^[^。、！？!?,\.]+/);
  return match ? match[0] : firstText.slice(0, 20);
};

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

  // 現在のスライド画像（slideIndexがあればそれを使い、なければindexを使用）
  const slideNum = currentSlide?.slideIndex ?? currentSlide?.index;
  const currentSlideImage = currentSlide && slideNum
    ? staticFile(`slides/slide_${String(slideNum).padStart(2, '0')}.png`)
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

  // スライドタイトルを取得
  const slideTitle = currentSlide?.title || extractTitleFromSubtitles(currentSlide?.subtitles || []);

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

      {/* タイトルスクロール（スライド上部） */}
      {currentSlide && (
        <TitleScroller title={slideTitle} frame={frame} />
      )}

      {/* スライド画像（16:9エリアにピッタリ配置） */}
      {currentSlideImage && (
        <div
          style={{
            position: "absolute",
            left: LAYOUT.slide.x,
            top: LAYOUT.slide.y,
            width: LAYOUT.slide.width,
            height: LAYOUT.slide.height,
            opacity,
            transform: `translateY(${translateY}px)`,
            zIndex: 1,
            overflow: "hidden",
          }}
        >
          <Img
            src={currentSlideImage}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
            }}
          />
        </div>
      )}

      {/* キャラクター（右下、下半身見切れ） */}
      <div
        style={{
          position: "absolute",
          bottom: LAYOUT.character.bottom,
          right: LAYOUT.character.right,
          height: LAYOUT.character.height,
          zIndex: 3,
        }}
      >
        <Img src={imageToShow} style={{ height: "100%" }} />
      </div>

      {/* 字幕（RPG風メッセージウィンドウ） */}
      {currentSubtitle && (
        <RPGSubtitle text={currentSubtitle.text} />
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
