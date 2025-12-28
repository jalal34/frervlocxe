import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

type Language = 'en' | 'ar';

interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
  isRTL: boolean;
}

const translations = {
  en: {
    // Header
    'app.name': 'VEXLO',
    'app.tagline': 'Premium Downloads',
    'header.noWatermark': 'No Watermark',
    
    // Hero
    'hero.badge': 'Premium Quality • Unlimited',
    'hero.title1': 'Download Videos',
    'hero.title2': 'In Stunning Quality',
    'hero.description': 'Experience the fastest video downloader. Paste any link from YouTube, TikTok, Instagram and get your content in seconds.',
    'hero.placeholder': 'Paste your video link here...',
    'hero.download': 'Get Video',
    'hero.processing': 'Analyzing...',
    
    // Platforms
    'platforms.supported': 'Trusted by millions',
    
    // How it works
    'howItWorks.title': 'Simple',
    'howItWorks.titleHighlight': 'Process',
    'howItWorks.step1.title': 'Paste Link',
    'howItWorks.step1.desc': 'Copy the video URL from your favorite platform',
    'howItWorks.step2.title': 'Select Quality',
    'howItWorks.step2.desc': 'Choose from HD, Full HD, or audio only',
    'howItWorks.step3.title': 'Download',
    'howItWorks.step3.desc': 'Get your file instantly, no waiting',
    
    // Video Result
    'video.views': 'views',
    'video.downloadOptions': 'Available Formats',
    'video.selectFormat': 'Select a format',
    'video.downloadNow': 'Download Now',
    'video.selected': 'Selected',
    
    // Footer
    'footer.lightningFast': 'Lightning Fast',
    'footer.lightningFastDesc': 'Powered by next-gen technology for instant results',
    'footer.safe': 'Secure & Private',
    'footer.safeDesc': 'Your privacy matters. Zero data collection.',
    'footer.free': 'Always Free',
    'footer.freeDesc': 'Premium features without premium prices',
    'footer.copyright': '© {year} Vexlo. All rights reserved.',
    'footer.disclaimer': 'For personal use only. Respect content creators.',
    
    // Toasts
    'toast.enterUrl': 'Please enter a video URL',
    'toast.invalidUrl': 'Invalid URL format',
    'toast.invalidUrlDesc': 'Include https:// or http://',
    'toast.error': 'Download failed',
    'toast.errorDesc': 'Could not fetch video. Please try again.',
    'toast.networkError': 'Network error. Please try again.',
    'toast.videoFound': 'Video ready!',
    'toast.videoFoundDesc': 'Choose your preferred quality',
    'toast.startingDownload': 'Downloading:',
    'toast.downloadDesc': 'Your file will be ready shortly',
    'toast.selectFormat': 'Select a format first',
    
    // Theme
    'theme.light': 'Light',
    'theme.dark': 'Dark',
  },
  ar: {
    // Header
    'app.name': 'VEXLO',
    'app.tagline': 'تحميل اسرع',
    'header.noWatermark': 'بدون علامة مائية',
    
    // Hero
    'hero.badge': 'جودة فائقة بلا حدود',
    'hero.title1': 'حمل الفيديوهات',
    'hero.title2': 'بجودة استثنائية',
    'hero.description': 'اختبر اسرع اداة تحميل فيديو. الصق اي رابط من يوتيوب او تيك توك او انستغرام واحصل على المحتوى في ثوان.',
    'hero.placeholder': 'الصق رابط الفيديو هنا...',
    'hero.download': 'جلب الفيديو',
    'hero.processing': 'جاري التحليل...',
    
    // Platforms
    'platforms.supported': 'موثوق من الملايين',
    
    // How it works
    'howItWorks.title': 'خطوات',
    'howItWorks.titleHighlight': 'بسيطة',
    'howItWorks.step1.title': 'الصق الرابط',
    'howItWorks.step1.desc': 'انسخ رابط الفيديو من منصتك المفضلة',
    'howItWorks.step2.title': 'اختر الجودة',
    'howItWorks.step2.desc': 'اختر من HD او Full HD او صوت فقط',
    'howItWorks.step3.title': 'حمل',
    'howItWorks.step3.desc': 'احصل على ملفك فورا بدون انتظار',
    
    // Video Result
    'video.views': 'مشاهدة',
    'video.downloadOptions': 'الصيغ المتاحة',
    'video.selectFormat': 'اختر صيغة',
    'video.downloadNow': 'تحميل الان',
    'video.selected': 'محدد',
    
    // Footer
    'footer.lightningFast': 'سرعة البرق',
    'footer.lightningFastDesc': 'مدعوم بتقنية الجيل القادم لنتائج فورية',
    'footer.safe': 'امن وخاص',
    'footer.safeDesc': 'خصوصيتك مهمة ولا نجمع اي بيانات',
    'footer.free': 'مجاني دائما',
    'footer.freeDesc': 'ميزات متميزة بدون اسعار متميزة',
    'footer.copyright': '{year} Vexlo جميع الحقوق محفوظة',
    'footer.disclaimer': 'للاستخدام الشخصي فقط واحترم صناع المحتوى',
    
    // Toasts
    'toast.enterUrl': 'الرجاء ادخال رابط الفيديو',
    'toast.invalidUrl': 'صيغة الرابط غير صحيحة',
    'toast.invalidUrlDesc': 'تاكد من تضمين https او http',
    'toast.error': 'فشل التحميل',
    'toast.errorDesc': 'تعذر جلب الفيديو. يرجى المحاولة مرة اخرى.',
    'toast.networkError': 'خطأ في الشبكة. يرجى المحاولة مرة اخرى.',
    'toast.videoFound': 'الفيديو جاهز',
    'toast.videoFoundDesc': 'اختر الجودة المفضلة',
    'toast.startingDownload': 'جاري التحميل',
    'toast.downloadDesc': 'ملفك سيكون جاهزا قريبا',
    'toast.selectFormat': 'اختر صيغة اولا',
    
    // Theme
    'theme.light': 'فاتح',
    'theme.dark': 'داكن',
  },
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const getInitialLanguage = (): Language => {
  const saved = localStorage.getItem('language');
  if (saved === 'en' || saved === 'ar') return saved;
  
  const browserLang = navigator.language.toLowerCase();
  if (browserLang.startsWith('ar')) return 'ar';
  return 'en';
};

export const LanguageProvider = ({ children }: { children: ReactNode }) => {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage);

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem('language', lang);
  };

  const t = (key: string): string => {
    const value = translations[language][key as keyof typeof translations['en']];
    return value || key;
  };

  const isRTL = language === 'ar';

  useEffect(() => {
    document.documentElement.dir = isRTL ? 'rtl' : 'ltr';
    document.documentElement.lang = language;
  }, [language, isRTL]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, isRTL }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};
