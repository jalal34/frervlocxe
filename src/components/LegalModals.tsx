import { useState } from 'react';
import { X, Shield, FileText, CheckCircle, AlertCircle, Lock, Eye, Globe, Users, Scale } from 'lucide-react';
import { useLanguage } from '@/hooks/useLanguage';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

const LegalModals = () => {
  const { language, isRTL } = useLanguage();
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [termsOpen, setTermsOpen] = useState(false);

  const privacyContent = {
    en: {
      title: 'Privacy Policy',
      sections: [
        {
          icon: Eye,
          title: 'Information We Collect',
          content: 'We do not collect personal information. Our service operates without user accounts or registration. The only data processed is the video URLs you provide, which are used solely to fetch the requested content.',
        },
        {
          icon: Lock,
          title: 'Data Security',
          content: 'Your privacy is our priority. All connections are encrypted using industry-standard SSL/TLS protocols. We do not store your video URLs, download history, or any identifiable information on our servers.',
        },
        {
          icon: Globe,
          title: 'Cookies & Tracking',
          content: 'We use minimal cookies only for essential functionality like language preferences and theme settings. We do not use tracking cookies, analytics that identify you, or any third-party advertising trackers.',
        },
        {
          icon: Users,
          title: 'Third-Party Services',
          content: 'Our service may display advertisements through Google AdSense. These third parties may use cookies according to their own privacy policies. We recommend reviewing their policies for complete transparency.',
        },
        {
          icon: Shield,
          title: 'Your Rights',
          content: 'You have the right to browse our service anonymously. Since we do not collect personal data, there is no data to request, modify, or delete. Your privacy is protected by design.',
        },
      ],
    },
    ar: {
      title: 'سياسة الخصوصية',
      sections: [
        {
          icon: Eye,
          title: 'المعلومات التي نجمعها',
          content: 'نحن لا نجمع معلومات شخصية. خدمتنا تعمل بدون حسابات مستخدمين او تسجيل. البيانات الوحيدة التي تتم معالجتها هي روابط الفيديو التي تقدمها والتي تستخدم فقط لجلب المحتوى المطلوب.',
        },
        {
          icon: Lock,
          title: 'امان البيانات',
          content: 'خصوصيتك هي اولويتنا. جميع الاتصالات مشفرة باستخدام بروتوكولات SSL/TLS القياسية. نحن لا نخزن روابط الفيديو او سجل التحميل او اي معلومات يمكن التعرف عليها.',
        },
        {
          icon: Globe,
          title: 'ملفات تعريف الارتباط والتتبع',
          content: 'نستخدم ملفات تعريف ارتباط بسيطة فقط للوظائف الاساسية مثل تفضيلات اللغة واعدادات السمة. نحن لا نستخدم ملفات تتبع او تحليلات تحددك.',
        },
        {
          icon: Users,
          title: 'خدمات الطرف الثالث',
          content: 'قد تعرض خدمتنا اعلانات من خلال Google AdSense. قد تستخدم هذه الاطراف ملفات تعريف الارتباط وفقا لسياسات الخصوصية الخاصة بها. ننصح بمراجعة سياساتهم.',
        },
        {
          icon: Shield,
          title: 'حقوقك',
          content: 'لديك الحق في تصفح خدمتنا بشكل مجهول. نظرا لاننا لا نجمع بيانات شخصية فلا توجد بيانات لطلبها او تعديلها او حذفها. خصوصيتك محمية بالتصميم.',
        },
      ],
    },
  };

  const termsContent = {
    en: {
      title: 'Terms of Use',
      
      sections: [
        {
          icon: FileText,
          title: 'Acceptance of Terms',
          content: 'By accessing and using VEXLO, you agree to be bound by these Terms of Use. If you do not agree with any part of these terms, please discontinue use of our service immediately.',
        },
        {
          icon: CheckCircle,
          title: 'Permitted Use',
          content: 'This service is intended for personal, non-commercial use only. You may download content that you have the right to access. Downloading copyrighted content without permission is strictly prohibited.',
        },
        {
          icon: AlertCircle,
          title: 'Prohibited Activities',
          content: 'You may not use this service to: download content you do not have rights to, distribute copyrighted material, engage in any illegal activities, attempt to bypass security measures, or overload our servers.',
        },
        {
          icon: Scale,
          title: 'Intellectual Property',
          content: 'All content downloaded through our service remains the property of its original creators. We do not claim ownership of any downloaded content. Respect copyright laws and content creator rights.',
        },
        {
          icon: Shield,
          title: 'Disclaimer of Liability',
          content: 'VEXLO provides this service as-is without warranties. We are not responsible for the content you download or how you use it. Users are solely responsible for ensuring their use complies with applicable laws.',
        },
        {
          icon: Lock,
          title: 'Service Modifications',
          content: 'We reserve the right to modify, suspend, or discontinue any aspect of our service at any time without notice. We may also update these terms periodically. Continued use constitutes acceptance of changes.',
        },
      ],
    },
    ar: {
      title: 'شروط الاستخدام',
      
      sections: [
        {
          icon: FileText,
          title: 'قبول الشروط',
          content: 'باستخدامك لموقع VEXLO فانت توافق على الالتزام بشروط الاستخدام هذه. اذا كنت لا توافق على اي جزء من هذه الشروط يرجى التوقف عن استخدام خدمتنا فورا.',
        },
        {
          icon: CheckCircle,
          title: 'الاستخدام المسموح',
          content: 'هذه الخدمة مخصصة للاستخدام الشخصي غير التجاري فقط. يمكنك تحميل المحتوى الذي لديك حق الوصول اليه. تحميل المحتوى المحمي بحقوق الطبع والنشر بدون اذن محظور تماما.',
        },
        {
          icon: AlertCircle,
          title: 'الانشطة المحظورة',
          content: 'لا يجوز لك استخدام هذه الخدمة لتحميل محتوى ليس لديك حقوق عليه او توزيع مواد محمية او الانخراط في انشطة غير قانونية او محاولة تجاوز اجراءات الامان.',
        },
        {
          icon: Scale,
          title: 'الملكية الفكرية',
          content: 'جميع المحتويات المحملة عبر خدمتنا تبقى ملكا لمنشئيها الاصليين. نحن لا ندعي ملكية اي محتوى تم تحميله. احترم قوانين حقوق الطبع والنشر وحقوق صناع المحتوى.',
        },
        {
          icon: Shield,
          title: 'اخلاء المسؤولية',
          content: 'تقدم VEXLO هذه الخدمة كما هي بدون ضمانات. نحن لسنا مسؤولين عن المحتوى الذي تقوم بتحميله او كيفية استخدامه. المستخدمون مسؤولون وحدهم عن ضمان امتثالهم للقوانين.',
        },
        {
          icon: Lock,
          title: 'تعديلات الخدمة',
          content: 'نحتفظ بالحق في تعديل او تعليق او ايقاف اي جانب من جوانب خدمتنا في اي وقت دون اشعار. قد نقوم ايضا بتحديث هذه الشروط دوريا. الاستمرار في الاستخدام يعني قبول التغييرات.',
        },
      ],
    },
  };

  const currentPrivacy = privacyContent[language];
  const currentTerms = termsContent[language];

  const ModalContent = ({ sections }: { 
    title: string; 
    sections: { icon: any; title: string; content: string }[] 
  }) => (
    <div className="space-y-6 text-start">
      
      {sections.map((section, index) => (
        <div 
          key={index} 
          className="group p-4 rounded-2xl bg-card/30 border border-border/20 hover:border-primary/30 transition-all duration-300"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform duration-300">
              <section.icon className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-foreground mb-2 text-lg">{section.title}</h3>
              <p className="text-muted-foreground leading-relaxed text-sm">{section.content}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="flex items-center gap-4">
      {/* Privacy Policy */}
      <Dialog open={privacyOpen} onOpenChange={setPrivacyOpen}>
        <DialogTrigger asChild>
          <button className="text-sm text-muted-foreground hover:text-primary transition-colors duration-300 flex items-center gap-2 group">
            <Shield className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" />
            <span>{currentPrivacy.title}</span>
          </button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto glass-card border-border/30">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-gradient text-start">
              {currentPrivacy.title}
            </DialogTitle>
          </DialogHeader>
          <ModalContent {...currentPrivacy} />
        </DialogContent>
      </Dialog>

      <span className="text-muted-foreground/30">|</span>

      {/* Terms of Use */}
      <Dialog open={termsOpen} onOpenChange={setTermsOpen}>
        <DialogTrigger asChild>
          <button className="text-sm text-muted-foreground hover:text-primary transition-colors duration-300 flex items-center gap-2 group">
            <FileText className="w-4 h-4 group-hover:scale-110 transition-transform duration-300" />
            <span>{currentTerms.title}</span>
          </button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto glass-card border-border/30">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-gradient text-start">
              {currentTerms.title}
            </DialogTitle>
          </DialogHeader>
          <ModalContent {...currentTerms} />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default LegalModals;
