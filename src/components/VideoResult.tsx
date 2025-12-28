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

  const videoDownloadUrl = `$1&type=video&stream=1&filename=${encodeURIComponent(video.title)}`;
  const audioDownloadUrl = `$1&type=audio&stream=1&filename=${encodeURIComponent(video.title)}`;

  return (
    <div className="glass-card-premium p-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Thumbnail */}
        <div className="relative flex-shrink-0 w-full lg:w-96 aspect-video rounded-2xl overflow-hidden group">
          <img
            src={video.thumbnail}
            alt={video.title}
            className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/20 to-transparent" />
          
          {/* Platform & Duration badges */}
          <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
            <span className="platform-badge">{video.platform}</span>
            {video.duration && (
              <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background/70 text-sm backdrop-blur-md font-medium">
                <Clock className="w-3.5 h-3.5" />
                {video.duration}
              </span>
            )}
          </div>
          
          {/* Play overlay */}
          <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <div className="w-16 h-16 rounded-full bg-primary/90 flex items-center justify-center backdrop-blur-sm">
              <div className="w-0 h-0 border-l-[20px] border-l-background border-y-[12px] border-y-transparent ml-1" />
            </div>
          </div>
        </div>

        {/* Info & Downloads */}
        <div className="flex-1 flex flex-col gap-6">
          <div>
            <h3 className="text-2xl font-bold text-foreground line-clamp-2 mb-3">
              {video.title}
            </h3>
            {video.views && (
              <p className="flex items-center gap-2 text-muted-foreground">
                <Eye className="w-4 h-4" />
                <span>{video.views} {t('video.views')}</span>
              </p>
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
                onClick={(e) => { e.preventDefault(); downloadViaFetch(videoDownloadUrl, `${video.title}.mp4`); }}
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
                onClick={(e) => { e.preventDefault(); downloadViaFetch(audioDownloadUrl, `${video.title}.mp3`); }}
                className="download-option-btn group flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-primary text-background">
                    <Music className="w-5 h-5" />
                  </div>
                  <span className="font-semibold">{t('video.downloadAudio')}</span>
                </div>
                <Download className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VideoResult;
