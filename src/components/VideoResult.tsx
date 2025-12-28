import { Download, Music, Video, Clock, Eye } from 'lucide-react';
import { useLanguage } from '@/hooks/useLanguage';

interface VideoInfo {
  title: string;
  thumbnail: string;
  duration: string;
  platform: string;
  views?: string;
}

interface VideoResultProps {
  video: VideoInfo;
  originalUrl: string;
  onDownload: (format: string) => void;
}

const VideoResult = ({ video, originalUrl }: VideoResultProps) => {
  const { t } = useLanguage();

  const downloadViaFetch = async (apiUrl: string, suggestedName: string) => {
    try {
      const res = await fetch(apiUrl);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = suggestedName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(objectUrl);
    } catch (e) {
      // fallback: normal navigation
      window.location.href = apiUrl;
    }
  };

  const baseProxy = `/api/proxy?url=${encodeURIComponent(originalUrl)}&stream=1&filename=${encodeURIComponent(
    video.title
  )}`;

  const videoDownloadUrl = `${baseProxy}&type=video`;
  const audioDownloadUrl = `${baseProxy}&type=audio`;

  return (
    <div className="w-full max-w-4xl mx-auto mt-8">
      <div className="relative overflow-hidden rounded-3xl bg-white/10 backdrop-blur-xl border border-white/20 shadow-2xl">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/10" />

        <div className="relative p-6 md:p-8">
          <div className="flex flex-col md:flex-row gap-6 md:gap-8">
            {/* Thumbnail */}
            <div className="relative flex-shrink-0">
              <div className="w-full md:w-64 aspect-video rounded-2xl overflow-hidden bg-black/20 shadow-lg">
                {video.thumbnail ? (
                  <img
                    src={video.thumbnail}
                    alt={video.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                    <Video className="w-12 h-12" />
                  </div>
                )}
              </div>

              <div className="absolute top-3 left-3 px-3 py-1 rounded-full bg-black/60 backdrop-blur-sm text-white text-sm font-medium">
                {video.platform}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 space-y-4">
              <h3 className="text-xl md:text-2xl font-bold text-foreground leading-tight">
                {video.title}
              </h3>

              <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                {video.duration && (
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    <span>{video.duration}</span>
                  </div>
                )}
                {video.views && (
                  <div className="flex items-center gap-2">
                    <Eye className="w-4 h-4" />
                    <span>{video.views}</span>
                  </div>
                )}
              </div>

              {/* Download Buttons */}
              <div className="flex flex-col gap-4">
                <p className="text-sm text-muted-foreground font-medium uppercase tracking-wider">
                  {t('video.downloadOptions')}
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Video Download */}
                  <a
                    href={videoDownloadUrl}
                    target="_self"
                    onClick={(e) => {
                      e.preventDefault();
                      downloadViaFetch(videoDownloadUrl, `${video.title}.mp4`);
                    }}
                    className="download-option-btn group flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-primary text-background">
                        <Video className="w-5 h-5" />
                      </div>
                      <span className="font-semibold">{t('video.downloadVideo')}</span>
                    </div>
                    <Download className="w-5 h-5" />
                  </a>

                  {/* Audio Download */}
                  <a
                    href={audioDownloadUrl}
                    target="_self"
                    onClick={(e) => {
                      e.preventDefault();
                      downloadViaFetch(audioDownloadUrl, `${video.title}.mp3`);
                    }}
                    className="download-option-btn group flex items-center justify-between"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-accent text-background">
                        <Music className="w-5 h-5" />
                      </div>
                      <span className="font-semibold">{t('video.downloadAudio')}</span>
                    </div>
                    <Download className="w-5 h-5" />
                  </a>
                </div>

                <p className="text-xs text-muted-foreground/80">
                  ملاحظة: بعض المنصات قد تعطي الصوت بصيغة m4a لكن سيتم تنزيله مباشرة.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoResult;