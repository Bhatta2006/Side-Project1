import type { MessageKey } from './en';

export const hi: Partial<Record<MessageKey, string>> = {
  'today.build.title': 'अपना कोर्स बनाएँ',
  'today.build.body': 'कोई भी विषय चुनें और बताएँ कि आप उसे कैसे सीखना चाहते हैं।',
  'settings.language.title': 'भाषा',
  'settings.language.help': 'पाठों, ट्यूटर और मेन्यू की भाषा, जहाँ हमारे पास अनुवाद है। कोड और तकनीकी शब्द अंग्रेज़ी में ही रहते हैं।',
  'settings.language.preview': 'प्रीव्यू: इस भाषा का अनुवाद मशीन से हुआ है और किसी व्यक्ति ने अभी इसे जाँचा नहीं है।',
  'settings.language.saved': 'भाषा सहेज ली गई।',
  'translation.machine': 'मशीन से अनुवादित। किसी व्यक्ति ने इसे अभी जाँचा नहीं है।',
  'translation.reviewed': '{name} द्वारा जाँचा गया।',
  'translation.english': 'अंग्रेज़ी मूल पाठ दिखाएँ',
};
