import { useState, FormEvent } from 'react';
import { Search, Download } from 'lucide-react';
import { toast } from 'sonner';
import { useLanguage } from '@/hooks/useLanguage';
import Header from '@/components/Header';
import Footer from '@/components/Footer';
import AdPlaceholder from '@/components/AdPlaceholder';
import VideoResult from '@/components/VideoResult';
import PlatformIcons from '@/components/PlatformIcons';

interface VideoFormat {
  quality: string;
  type: 'video' | 'audio';
  size: string;
  format_id?: string;
}

interface VideoData {
  title: string;
  thumbnail: string;
  duration: string;
  platform: string;
  views: string;
  formats: VideoFormat[];
  download_url?: string;
  hdplay?: string;
  play?: string;
  music?: string;
}

const Index = () => {
  const { t, isRTL } = useLanguage();
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [videoData, setVideoData] = useState<VideoData | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    const trimmedUrl = url.trim();

    // Only check if URL is not empty and starts with http
    if (!trimmedUrl) {
      toast.error(t('toast.enterUrl'));
      return;
    }

    if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
      toast.error(t('toast.invalidUrl'), {
        description: t('toast.invalidUrlDesc'),
      });
      return;
    }

    setIsLoading(true);
    setVideoData(null);

    try {
      // Send all URLs to the backend API
      const response = await fetch(`/api/download?url=${encodeURIComponent(trimmedUrl)}`);
      const data = await response.json();

      if (data.status === 'success' && data.data) {
        const videoInfo = data.data;
        
        // Determine platform from URL
        let platform = 'Video';
        if (trimmedUrl.includes('tiktok.com')) platform = 'TikTok';
        else if (trimmedUrl.includes('youtube.com') || trimmedUrl.includes('youtu.be')) platform = 'YouTube';
        else if (trimmedUrl.includes('instagram.com')) platform = 'Instagram';
        else if (trimmedUrl.includes('facebook.com') || trimmedUrl.includes('fb.watch')) platform = 'Facebook';
        else if (trimmedUrl.includes('twitter.com') || trimmedUrl.includes('x.com')) platform = 'Twitter/X';
        else if (trimmedUrl.includes('vimeo.com')) platform = 'Vimeo';
        else if (trimmedUrl.includes('snapchat.com')) platform = 'Snapchat';
        else if (trimmedUrl.includes('pinterest.com')) platform = 'Pinterest';

        setVideoData({
          title: videoInfo.title || 'Video',
          thumbnail: videoInfo.thumbnail || '',
          duration: videoInfo.duration || '',
          platform: platform,
          views: '',
          formats: [
            { quality: 'HD Video', type: 'video' as const, size: '' },
            { quality: 'Audio Only', type: 'audio' as const, size: '' },
          ],
          download_url: videoInfo.download_url || '',
        });
        toast.success(t('toast.videoFound'), {
          description: t('toast.videoFoundDesc'),
        });
      } else {
        toast.error(t('toast.error'), {
          description: data.message || t('toast.errorDesc'),
        });
      }
    } catch (error) {
      console.error('Request error:', error);
      toast.error(t('toast.error'), {
        description: t('toast.networkError'),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = (format: string) => {
    toast.info(`${t('toast.startingDownload')} ${format}`, {
      description: t('toast.downloadDesc'),
    });
  };

  const howItWorksSteps = [
    { step: '1', title: t('howItWorks.step1.title'), desc: t('howItWorks.step1.desc') },
    { step: '2', title: t('howItWorks.step2.title'), desc: t('howItWorks.step2.desc') },
    { step: '3', title: t('howItWorks.step3.title'), desc: t('howItWorks.step3.desc') },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-grid">
      {/* Premium Mesh Background */}
      <div className="fixed inset-0 pointer-events-none bg-mesh" />
      
      {/* Animated orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-20 left-[10%] w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] animate-float" />
        <div className="absolute bottom-20 right-[10%] w-[400px] h-[400px] bg-secondary/5 rounded-full blur-[100px] animate-float" style={{ animationDelay: '-3s' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/3 rounded-full blur-[150px]" />
      </div>

      <Header />

      <main className="flex-1 relative z-10">
        <div className="container mx-auto px-4 py-4 md:py-8">
          {/* Header Ad - Hidden on mobile for immediate search visibility */}
          <AdPlaceholder position="header" className="mb-6 md:mb-10 hidden md:flex" />

          {/* Hero Section - Compact on mobile */}
          <section className="text-center max-w-5xl mx-auto mb-8 md:mb-16">
            {/* Premium Badge - New Design */}
            <div className="inline-flex items-center gap-2 md:gap-3 px-4 md:px-6 py-2 md:py-3 rounded-2xl bg-gradient-to-r from-primary/20 to-secondary/20 border border-primary/30 mb-4 md:mb-8 backdrop-blur-sm shadow-lg shadow-primary/10">
              <Download className="w-4 h-4 md:w-5 md:h-5 text-primary" />
              <span className="text-xs md:text-sm text-foreground font-bold tracking-wide">{t('hero.badge')}</span>
            </div>
            
            {/* Title - Smaller on mobile */}
            <h1 className="text-3xl sm:text-5xl lg:text-7xl font-bold mb-3 md:mb-8 leading-tight">
              <span className="text-foreground">{t('hero.title1')}</span>
              <br />
              <span className="text-gradient">{t('hero.title2')}</span>
            </h1>
            
            {/* Description - Hidden on mobile for compact view */}
            <p className="hidden md:block text-xl text-muted-foreground max-w-2xl mx-auto mb-12 leading-relaxed">
              {t('hero.description')}
            </p>

            {/* Premium Search Form - Immediately visible */}
            <form onSubmit={handleSubmit} className="relative max-w-3xl mx-auto mt-4 md:mt-0">
              <div className="relative group">
                {/* Glow effect */}
                <div className="absolute -inset-1 bg-gradient-to-r from-primary via-secondary to-primary rounded-2xl md:rounded-3xl opacity-20 blur-xl group-focus-within:opacity-40 transition-all duration-500" />
                
                <div className="relative flex items-center bg-card rounded-xl md:rounded-2xl overflow-hidden border border-border/50 shadow-2xl shadow-background/50">
                  <div className="pl-4 md:pl-6">
                    <Search className="w-5 h-5 md:w-6 md:h-6 text-muted-foreground" />
                  </div>
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder={t('hero.placeholder')}
                    className="glow-input flex-1 bg-transparent border-none text-base md:text-lg py-4 md:py-5 text-start"
                    disabled={isLoading}
                    dir={isRTL ? 'rtl' : 'ltr'}
                  />
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="gradient-button m-1.5 md:m-2 px-4 md:px-8 py-3 md:py-4 flex items-center gap-2 md:gap-3"
                  >
                    {isLoading ? (
                      <div className="w-5 h-5 border-2 border-background/30 border-t-background rounded-full animate-spin" />
                    ) : (
                      <>
                        <Download className="w-5 h-5" />
                        <span className="hidden sm:inline">{t('hero.download')}</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>

            {/* Platform Icons - Smaller on mobile */}
            <div className="mt-6 md:mt-10">
              <PlatformIcons />
            </div>
          </section>

          {/* Below Search Ad */}
          <AdPlaceholder position="below-search" className="mb-12 max-w-4xl mx-auto" />

          {/* Results Section */}
          <section className="max-w-5xl mx-auto">

            {videoData && !isLoading && (
              <>
                <AdPlaceholder position="before-download" className="mb-8" />
                <VideoResult video={videoData} originalUrl={url} onDownload={handleDownload} />
              </>
            )}
          </section>

          {/* How It Works */}
          {!videoData && !isLoading && (
            <section className="max-w-5xl mx-auto mt-24">
              <h2 className="text-3xl font-bold text-center mb-12">
                {t('howItWorks.title')} <span className="text-gradient">{t('howItWorks.titleHighlight')}</span>
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                {howItWorksSteps.map((item, index) => (
                  <div key={item.step} className="step-card group" style={{ animationDelay: `${index * 0.1}s` }}>
                    <div className="step-number group-hover:scale-110 transition-transform duration-300">
                      {item.step}
                    </div>
                    <h3 className="font-bold text-xl text-foreground mb-3">{item.title}</h3>
                    <p className="text-muted-foreground leading-relaxed">{item.desc}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </main>

      {/* Footer Ad */}
      <div className="container mx-auto px-4 pb-8">
        <AdPlaceholder position="footer" />
      </div>

      <Footer />
    </div>
  );
};

export default Index;
