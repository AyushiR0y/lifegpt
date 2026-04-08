"""
Transliteration Rules for Multi-Language PDF Translation

This module contains:
- TRANSLITERATE_WORDS: Words that need language-specific transliterations
- KEEP_ORIGINAL_WORDS: Words that should remain untranslated (brand names, etc.)
- Helper functions to retrieve language-specific translations
"""

# ============================================================================
# TRANSLITERATE_WORDS - Language-Specific Transliterations
# ============================================================================
# Format: "english_word": {"language_key": "transliterated_form"}
# Add new words following this pattern

TRANSLITERATE_WORDS = {

  "google": {
    "hindi": "गूगल",
    "tamil": "கூகுள்",
    "telugu": "గూగుల్",
    "malayalam": "ഗൂഗിൾ",
    "bengali": "গুগল",
    "gujarati": "ગુગલ",
    "marathi": "गूगल",
    "punjabi": "ਗੂਗਲ",
    "odia": "ଗୁଗଲ",
    "assamese": "গুগল"
  },
  "microsoft": {
    "hindi": "माइक्रोसॉफ्ट",
    "tamil": "மைக்ரோசாஃப்ட்",
    "telugu": "మైక్రోసాఫ్ట్",
    "malayalam": "മൈക്രോസോഫ്റ്റ്",
    "bengali": "মাইক্রোসফ্ট",
    "gujarati": "માઇક્રોસોફ્ટ",
    "marathi": "मायक्रोसॉफ्ट",
    "punjabi": "ਮਾਈਕ੍ਰੋਸਾਫਟ",
    "odia": "ମାଇକ୍ରୋସଫ୍ଟ",
    "assamese": "মাইক্ৰোচফ্ট"
  },
  "amazon": {
    "hindi": "अमेज़न",
    "tamil": "அமேசான்",
    "telugu": "అమెజాన్",
    "malayalam": "അമേസോൺ",
    "bengali": "অ্যামাজন",
    "gujarati": "એમેઝોન",
    "marathi": "अमेझॉन",
    "punjabi": "ਅਮੇਜ਼ਨ",
    "odia": "ଆମେଜନ",
    "assamese": "আমাজন"
  },
  "facebook": {
    "hindi": "फेसबुक",
    "tamil": "ஃபேஸ்புக்",
    "telugu": "ఫేస్‌బుక్",
    "malayalam": "ഫേസ്ബുക്ക്",
    "bengali": "ফেসবুক",
    "gujarati": "ફેસબુક",
    "marathi": "फेसबुक",
    "punjabi": "ਫੇਸਬੁੱਕ",
    "odia": "ଫେସବୁକ",
    "assamese": "ফেচবুক"
  },
  "apple": {
    "hindi": "एप्पल",
    "tamil": "ஆப்பிள்",
    "telugu": "ఆపిల్",
    "malayalam": "ആപ്പിൾ",
    "bengali": "অ্যাপল",
    "gujarati": "એપલ",
    "marathi": "ॲपल",
    "punjabi": "ਐਪਲ",
    "odia": "ଆପଲ",
    "assamese": "এপল"
  },
  "email": {
    "hindi": "ईमेल",
    "tamil": "ஈமெயில்",
    "telugu": "ఈమెయిల్",
    "malayalam": "ഇമെയിൽ",
    "bengali": "ইমেল",
    "gujarati": "ઈમેલ",
    "marathi": "ईमेल",
    "punjabi": "ਈਮੇਲ",
    "odia": "ଈମେଲ",
    "assamese": "ইমেইল"
  },
  "internet": {
    "hindi": "इंटरनेट",
    "tamil": "இணையம்",
    "telugu": "ఇంటర్నెట్",
    "malayalam": "ഇന്റർനെറ്റ്",
    "bengali": "ইন্টারনেট",
    "gujarati": "ઇન્ટરનેટ",
    "marathi": "इंटरनेट",
    "punjabi": "ਇੰਟਰਨੈੱਟ",
    "odia": "ଇଣ୍ଟରନେଟ",
    "assamese": "ইণ্টাৰনেট"
  },
  "computer": {
    "hindi": "कंप्यूटर",
    "tamil": "கம்ப்யூட்டர்",
    "telugu": "కంప్యూటర్",
    "malayalam": "കമ്പ്യൂട്ടർ",
    "bengali": "কম্পিউটার",
    "gujarati": "કમ્પ્યુટર",
    "marathi": "कॉम्प्युटर",
    "punjabi": "ਕੰਪਿਊਟਰ",
    "odia": "କମ୍ପ୍ୟୁଟର",
    "assamese": "কম্পিউটাৰ"
  },
  "mobile": {
    "hindi": "मोबाइल",
    "tamil": "மொபைல்",
    "telugu": "మొబైల్",
    "malayalam": "മൊബൈൽ",
    "bengali": "মোবাইল",
    "gujarati": "મોબાઇલ",
    "marathi": "मोबाईल",
    "punjabi": "ਮੋਬਾਇਲ",
    "odia": "ମୋବାଇଲ",
    "assamese": "মোবাইল"
  },
  "software": {
    "hindi": "सॉफ्टवेयर",
    "tamil": "சாப்ட்வேர்",
    "telugu": "సాఫ్ట్‌వేర్",
    "malayalam": "സോഫ്റ്റ്വെയർ",
    "bengali": "সফটওয়্যার",
    "gujarati": "સોફ્ટવેર",
    "marathi": "सॉफ्टवेअर",
    "punjabi": "ਸਾਫਟਵੇਅਰ",
    "odia": "ସଫ୍ଟୱେୟାର",
    "assamese": "ছফ্টৱেৰ"
  },
  "website": {
    "hindi": "वेबसाइट",
    "tamil": "வெப்சைட்",
    "telugu": "వెబ్‌సైట్",
    "malayalam": "വെബ്സൈറ്റ്",
    "bengali": "ওয়েবসাইট",
    "gujarati": "વેબસાઇટ",
    "marathi": "वेबसाइट",
    "punjabi": "ਵੈੱਬਸਾਈਟ",
    "odia": "ୱେବସାଇଟ୍",
    "assamese": "ৱেবছাইট"

  },
  "fund": {
    "hindi": "फंड",
    "tamil": "பண்ட்",
    "telugu": "ఫండ్",
    "malayalam": "ഫണ്ട്",
    "bengali": "ফান্ড",
    "gujarati": "ફંડ",
    "marathi": "फंड",
    "punjabi": "ਫੰਡ",
    "odia": "ଫଣ୍ଡ",
    "assamese": "ফাণ্ড"
  },
  "plan": {
    "hindi": "प्लान",
    "tamil": "பிளான்",
    "telugu": "ప్లాన్",
    "malayalam": "പ്ലാൻ",
    "bengali": "প্ল্যান",
    "gujarati": "પ્લાન",
    "marathi": "प्लॅन",
    "punjabi": "ਪਲਾਨ",
    "odia": "ପ୍ଲାନ୍",
    "assamese": "প্লান"
  },
  "policy": {
    "hindi": "पॉलिसी",
    "tamil": "பாலிசி",
    "telugu": "పాలసీ",
    "malayalam": "പോളിസി",
    "bengali": "পলিসি",
    "gujarati": "પોલિસી",
    "marathi": "पॉलिसी",
    "punjabi": "ਪਾਲਿਸੀ",
    "odia": "ପଲିସି",
    "assamese": "পলিচি"
  },
  "premium": {
    "hindi": "प्रीमियम",
    "tamil": "ப்ரீமியம்",
    "telugu": "ప్రీమియం",
    "malayalam": "പ്രീമിയം",
    "bengali": "প্রিমিয়াম",
    "gujarati": "પ્રીમિયમ",
    "marathi": "प्रीमियम",
    "punjabi": "ਪ੍ਰੀਮੀਅਮ",
    "odia": "ପ୍ରିମିୟମ୍",
    "assamese": "প্ৰিমিয়াম"
  },
  "account": {
    "hindi": "अकाउंट",
    "tamil": "அக்கவுண்ட்",
    "telugu": "అకౌంట్",
    "malayalam": "അക്കൗണ്ട്",
    "bengali": "অ্যাকাউন্ট",
    "gujarati": "અકાઉન્ટ",
    "marathi": "अकाउंट",
    "punjabi": "ਅਕਾਊਂਟ",
    "odia": "ଅକାଉଣ୍ଟ",
    "assamese": "একাউণ্ট"
  },
  "insurance": {
    "hindi": "इंश्योरेंस",
    "tamil": "இன்ஷ்யூரன்ஸ்",
    "telugu": "ఇన్షూరెన్స్",
    "malayalam": "ഇൻഷുറൻസ്",
    "bengali": "ইনশিওরেন্স",
    "gujarati": "ઇન્શ્યોરન્સ",
    "marathi": "इन्शुरन्स",
    "punjabi": "ਇਨਸ਼ੂਰੈਂਸ",
    "odia":"ଇନ୍‌ଶୁରେନ୍ସ",
    "assamese": "ইনশুৰেন্স"
  },
  "loan": {
    "hindi": "लोन",
    "tamil": "லோன்",
    "telugu": "లోన్",
    "malayalam": "ലോൺ",
    "bengali": "লোন",
    "gujarati": "લોન",
    "marathi": "लोन",
    "punjabi": "ਲੋਨ",
    "odia": "ଲୋନ୍",
    "assamese": "লোন"
  },
  "market": {
    "hindi": "मार्केट",
    "tamil": "மார்க்கெட்",
    "telugu": "మార్కెట్",
    "malayalam": "മാർക്കറ്റ്",
    "bengali": "মার্কেট",
    "gujarati": "માર્કેટ",
    "marathi": "मार्केट",
    "punjabi": "ਮਾਰਕੀਟ",
    "odia": "ମାର୍କେଟ୍",
    "assamese": "মাৰ্কেট"
  },
  "Bima":{
    "hindi": "बीमा",
    "tamil": "பீமா",
    "telugu": "బీమా",
    "malayalam": "ബീമ",
    "bengali": "বিমা",
    "gujarati": "બીમા",
    "marathi": "बीमा",
    "punjabi": "ਬੀਮਾ",
    "odia": "ବୀମା",
    "assamese": "বীমা"
  },
  "Assured":{
    "hindi": "अशोरेड",
    "tamil": "அஷ்யூர்டு",
    "telugu": "అష్యూర్డ్",
    "malayalam": "അഷ്യൂർഡ്",
    "bengali": "অ্যাশুরড",
    "gujarati": "અશ્યોર્ડ",
    "marathi": "अशोर्ड",
    "punjabi": "ਅਸ਼ਿਊਰਡ", 
    "odia": "ଅଶ୍ୟୁର୍ଡ",
    "assamese": "অ্যাশুৰ্ড"
  },

  "investment": {
    "hindi": "इन्वेस्टमेंट",
    "tamil": "இன்வெஸ்ட்மெண்ட்",
    "telugu": "ఇన్వెస్ట్‌మెంట్",
    "malayalam": "ഇൻവെസ്റ്റ്‌മെന്റ്",
    "bengali": "ইনভেস্টমেন্ট",
    "gujarati": "ઇન્વેસ્ટમેન્ટ",
    "marathi": "इन्व्हेस्टमेंट",
    "punjabi": "ਇਨਵੈਸਟਮੈਂਟ",
    "odia": "ଇନ୍‌ଭେଷ୍ଟମେଣ୍ଟ",
    "assamese": "ইনভেষ্টমেণ্ট"
  },
  "investor": {
    "hindi": "इन्वेस्टर",
    "tamil": "இன்வெஸ்டர்",
    "telugu": "ఇన్వెస్టర్",
    "malayalam": "ഇൻവെസ്റ്റർ",
    "bengali": "ইনভেস্টর",
    "gujarati": "ઇન્વેસ્ટર",
    "marathi": "इन्व्हेस्टर",
    "punjabi": "ਇਨਵੈਸਟਰ",
    "odia": "ଇନ୍‌ଭେଷ୍ଟର",
    "assamese": "ইনভেষ্টৰ"
  },
  "finance": {
    "hindi": "फाइनेंस",
    "tamil": "ஃபைனான்ஸ்",
    "telugu": "ఫైనాన్స్",
    "malayalam": "ഫൈനാൻസ്",
    "bengali": "ফাইন্যান্স",
    "gujarati": "ફાઇનાન્સ",
    "marathi": "फायनान्स",
    "punjabi": "ਫਾਇਨੈਂਸ",
    "odia": "ଫାଇନାନ୍ସ",
    "assamese": "ফাইনেন্স"
  },
  "financial": {
    "hindi": "फाइनेंशियल",
    "tamil": "ஃபைனான்ஷியல்",
    "telugu": "ఫైనాన్షియల్",
    "malayalam": "ഫൈനാൻഷ്യൽ",
    "bengali": "ফাইন্যান্সিয়াল",
    "gujarati": "ફાઇનાન્સિયલ",
    "marathi": "फायनान्शियल",
    "punjabi": "ਫਾਇਨੈਂਸ਼ੀਅਲ",
    "odia": "ଫାଇନାନ୍‌ସିୟଲ୍",
    "assamese": "ফাইনেন্সিয়াল"
  },
  "payment": {
    "hindi": "पेमेंट",
    "tamil": "பேமெண்ட்",
    "telugu": "పేమెంట్",
    "malayalam": "പേയ്മെന്റ്",
    "bengali": "পেমেন্ট",
    "gujarati": "પેમેન્ટ",
    "marathi": "पेमेंट",
    "punjabi": "ਪੇਮੈਂਟ",
    "odia": "ପେମେଣ୍ଟ",
    "assamese": "পেমেন্ট"
  },
  "payments": {
    "hindi": "पेमेंट्स",
    "tamil": "பேமெண்ட்ஸ்",
    "telugu": "పేమెంట్స్",
    "malayalam": "പേയ്മെന്റ്സ്",
    "bengali": "পেমেন্টস",
    "gujarati": "પેમેન્ટ્સ",
    "marathi": "पेमेंट्स",
    "punjabi": "ਪੇਮੈਂਟਸ",
    "odia": "ପେମେଣ୍ଟସ୍",
    "assamese": "পেমেন্টছ"
  },
  "tax": {
    "hindi": "टैक्स",
    "tamil": "டாக்ஸ்",
    "telugu": "టాక్స్",
    "malayalam": "ടാക്സ്",
    "bengali": "ট্যাক্স",
    "gujarati": "ટેક્સ",
    "marathi": "टॅक्स",
    "punjabi": "ਟੈਕਸ",
    "odia": "ଟ୍ୟାକ୍ସ",
    "assamese": "টেক্স"
  },
  "credit": {
    "hindi": "क्रेडिट",
    "tamil": "கிரெடிட்",
    "telugu": "క్రెడిట్",
    "malayalam": "ക്രെഡിറ്റ്",
    "bengali": "ক্রেডিট",
    "gujarati": "ક્રેડિટ",
    "marathi": "क्रेडिट",
    "punjabi": "ਕ੍ਰੈਡਿਟ",
    "odia": "କ୍ରେଡିଟ୍",
    "assamese": "ক্ৰেডিট"
  },
  "debit": {
    "hindi": "डेबिट",
    "tamil": "டெபிட்",
    "telugu": "డెబిట్",
    "malayalam": "ഡെബിറ്റ്",
    "bengali": "ডেবিট",
    "gujarati": "ડેબિટ",
    "marathi": "डेबिट",
    "punjabi": "ਡੈਬਿਟ",
    "odia": "ଡେବିଟ୍",
    "assamese": "ডেবিট"
  },
  "balance": {
    "hindi": "बैलेंस",
    "tamil": "பேலன்ஸ்",
    "telugu": "బ్యాలెన్స్",
    "malayalam": "ബാലൻസ്",
    "bengali": "ব্যালেন্স",
    "gujarati": "બેલેન્સ",
    "marathi": "बॅलन्स",
    "punjabi": "ਬੈਲੈਂਸ",
    "odia": "ବ୍ୟାଲେନ୍ସ୍",
    "assamese": "ব্যালেন্স"
  },
  "profit": {
    "hindi": "प्रॉफिट",
    "tamil": "ப்ராஃபிட்",
    "telugu": "ప్రాఫిట్",
    "malayalam": "പ്രോഫിറ്റ്",
    "bengali": "প্রফিট",
    "gujarati": "પ્રોફિટ",
    "marathi": "प्रॉफिट",
    "punjabi": "ਪ੍ਰੋਫਿਟ",
    "odia": "ପ୍ରୋଫିଟ୍",
    "assamese": "প্রফিট"
  },
  "loss": {
    "hindi": "लॉस",
    "tamil": "லாஸ்",
    "telugu": "లాస్",
    "malayalam": "ലോസ്",
    "bengali": "লস",
    "gujarati": "લોસ",
    "marathi": "लॉस",
    "punjabi": "ਲੋਸ",
    "odia": "ଲୋସ୍",
    "assamese": "লস"
  },
  "revenue": {
    "hindi": "रेवेन्यू",
    "tamil": "ரெவன்யூ",
    "telugu": "రెవెన్యూ",
    "malayalam": "റെവന്യൂ",
    "bengali": "রেভিনিউ",
    "gujarati": "રેવન્યુ",
    "marathi": "रेव्हेन्यू",
    "punjabi": "ਰੇਵਨਯੂ",
    "odia": "ରେଭେନ୍ୟୁ",
    "assamese": "ৰিভেনিউ"
  },
  "interest": {
    "hindi": "इंटरेस्ट",
    "tamil": "இன்ட்ரஸ்ட்",
    "telugu": "ఇంట్రెస్ట్",
    "malayalam": "ഇന്ററെസ്റ്റ്",
    "bengali": "ইন্টারেস্ট",
    "gujarati": "ઇન્ટરેસ્ટ",
    "marathi": "इंटरेस्ट",
    "punjabi": "ਇੰਟਰੈਸਟ",
    "odia": "ଇଣ୍ଟରେଷ୍ଟ",
    "assamese": "ইণ্টাৰেষ্ট"
  },
  "rate": {
    "hindi": "रेट",
    "tamil": "ரேட்",
    "telugu": "రేట్",
    "malayalam": "റേറ്റ്",
    "bengali": "রেট",
    "gujarati": "રેટ",
    "marathi": "रेट",
    "punjabi": "ਰੇਟ",
    "odia": "ରେଟ୍",
    "assamese": "ৰেট"
  },
  "rates": {
    "hindi": "रेट्स",
    "tamil": "ரேட்ஸ்",
    "telugu": "రేట్స్",
    "malayalam": "റേറ്റ്സ്",
    "bengali": "রেটস",
    "gujarati": "રેટ્સ",
    "marathi": "रेट्स",
    "punjabi": "ਰੇਟਸ",
    "odia": "ରେଟ୍ସ",
    "assamese": "ৰেটছ"
  },
  "risk": {
    "hindi": "रिस्क",
    "tamil": "ரிஸ்க்",
    "telugu": "రిస్క్",
    "malayalam": "റിസ്ക്",
    "bengali": "রিস্ক",
    "gujarati": "રિસ્ક",
    "marathi": "रिस्क",
    "punjabi": "ਰਿਸਕ",
    "odia": "ରିସ୍କ୍",
    "assamese": "ৰিস্ক"
  },
  "return": {
    "hindi": "रिटर्न",
    "tamil": "ரிட்டர்ன்",
    "telugu": "రిటర్న్",
    "malayalam": "റിട്ടേൺ",
    "bengali": "রিটার্ন",
    "gujarati": "રિટર્ન",
    "marathi": "रिटर्न",
    "punjabi": "ਰੀਟਰਨ",
    "odia": "ରୀଟର୍ନ୍",
    "assamese": "ৰিটাৰ্ন"
  },
  "portfolio": {
    "hindi": "पोर्टफोलियो",
    "tamil": "போர்ட்ஃபோலியோ",
    "telugu": "పోర్ట్‌ఫోలియో",
    "malayalam": "പോർട്ട്ഫോളിയോ",
    "bengali": "পোর্টফোলিও",
    "gujarati": "પોર્ટફોલિયો",
    "marathi": "पोर्टफोलिओ",
    "punjabi": "ਪੋਰਟਫੋਲੀਓ",
    "odia": "ପୋର୍ଟଫୋଲିୟୋ",
    "assamese": "পোৰ্টফোলিও"
  },
  
  "policyholder": {
    "hindi": "पॉलिसीहोल्डर",
    "tamil": "பாலிசிஹோல்டர்",
    "telugu": "పాలసీహోల్డర్",
    "malayalam": "പോളിസി ഹോൾഡർ",
    "bengali": "পলিসিহোল্ডার",
    "gujarati": "પોલિસીહોલ્ડર",
    "marathi": "पॉलिसीहोल्डर",
    "punjabi": "ਪੋਲੀਸੀਹੋਲਡਰ",
    "odia": "ପୋଲିସୀହୋଲ୍ଡର୍",
    "assamese": "পলিসি হোল্ডাৰ"
  },
  "claim": {
    "hindi": "क्लेम",
    "tamil": "கிளெய்ம்",
    "telugu": "క్లెయిమ్",
    "malayalam": "ക്ലെയിം",
    "bengali": "ক্লেইম",
    "gujarati": "ક્લેમ",
    "marathi": "क्लेम"
  },
  "coverage": {
    "hindi": "कवरेज",
    "tamil": "கவரேஜ்",
    "telugu": "కవరేజ్",
    "malayalam": "കവറേജ്",
    "bengali": "কভারেজ",
    "gujarati": "કવરેજ",
    "marathi": "कव्हरेज"
  },
  "benefit": {
    "hindi": "बेनिफिट",
    "tamil": "பெனிபிட்",
    "telugu": "బెనిఫిట్",
    "malayalam": "ബെനിഫിറ്റ്",
    "bengali": "বেনিফিট",
    "gujarati": "બેનિફિટ",
    "marathi": "बेनिफिट"
  },
  "rider": {
    "hindi": "राइडर",
    "tamil": "ரைடர்",
    "telugu": "రైడర్",
    "malayalam": "റൈഡർ",
    "bengali": "রাইডার",
    "gujarati": "રાઇડર",
    "marathi": "रायडर"
  },
  "endorsement": {
    "hindi": "एंडोर्समेंट",
    "tamil": "எண்டோர்ஸ்மெண்ட்",
    "telugu": "ఎండోర్స్‌మెంట్",
    "malayalam": "എൻഡോഴ്‌സ്‌മെന്റ്",
    "bengali": "এন্ডোর্সমেন্ট",
    "gujarati": "એન્ડોર્સમેન્ટ",
    "marathi": "एंडोर्समेंट"
  },
  "deductible": {
    "hindi": "डिडक्टिबल",
    "tamil": "டிடக்டிபிள்",
    "telugu": "డిడక్టిబుల్",
    "malayalam": "ഡിഡക്ടിബിൾ",
    "bengali": "ডিডাক্টিবল",
    "gujarati": "ડિડક્ટિબલ",
    "marathi": "डिडक्टिबल"
  },
  "broker": {
    "hindi": "ब्रोकर",
    "tamil": "ப்ரோக்கர்",
    "telugu": "బ్రోకర్",
    "malayalam": "ബ്രോക്കർ",
    "bengali": "ব্রোকার",
    "gujarati": "બ્રોકર",
    "marathi": "ब्रोकर"
  },
  "insured": {
    "hindi": "इंश्योर्ड",
    "tamil": "இன்ஷ்யூர்ட்",
    "telugu": "ఇన్షూర్డ్",
    "malayalam": "ഇൻഷ്യൂർഡ്",
    "bengali": "ইনশিওর্ড",
    "gujarati": "ઇન્શ્યોર્ડ",
    "marathi": "इन्शुर्ड"
  },
  "insurer": {
    "hindi": "इंश्योरर",
    "tamil": "இன்ஷ்யூரர்",
    "telugu": "ఇన్షూరర్",
    "malayalam": "ഇൻഷുറർ",
    "bengali": "ইনশিওরার",
    "gujarati": "ઇન્શ્યોરર",
    "marathi": "इन्शुरर"
  },
  "beneficiary": {
    "hindi": "बेनिफिशियरी",
    "tamil": "பெனிஃபிஷியரி",
    "telugu": "బెనిఫిషియరీ",
    "malayalam": "ബെനിഫിഷ്യറി",
    "bengali": "বেনিফিশিয়ারি",
    "gujarati": "બેનિફિશિયરી",
    "marathi": "बेनिफिशियरी"
  },
  "hazard": {
    "hindi": "हैज़र्ड",
    "tamil": "ஹாசர்ட்",
    "telugu": "హాజర్డ్",
    "malayalam": "ഹാസർഡ്",
    "bengali": "হ্যাজার্ড",
    "gujarati": "હેઝર્ડ",
    "marathi": "हॅझर्ड"
  },
  "exclusion": {
    "hindi": "एक्सक्लूज़न",
    "tamil": "எக்ஸ்க்ளூஷன்",
    "telugu": "ఎక్స్‌క్లూజన్",
    "malayalam": "എക്സ്ക്ലൂഷൻ",
    "bengali": "এক্সক্লুশন",
    "gujarati": "એક્સક્લૂઝન",
    "marathi": "एक्सक्लूजन"
  },
  "inclusion": {
    "hindi": "इंक्लूजन",
    "tamil": "இன்க்ளூஷன்",
    "telugu": "ఇన్‌క్లూజన్",
    "malayalam": "ഇൻക്ലൂഷൻ",
    "bengali": "ইনক্লুশন",
    "gujarati": "ઇન્ક્લૂઝન",
    "marathi": "इन्क्लूजन"
  },
  "lapse": {
    "hindi": "लैप्स",
    "tamil": "லாப்ஸ்",
    "telugu": "లాప్స్",
    "malayalam": "ലാപ്സ്",
    "bengali": "ল্যাপ্স",
    "gujarati": "લેપ્સ",
    "marathi": "लॅप्स"
  },
  "renewal": {
    "hindi": "रिन्यूअल",
    "tamil": "ரினியூவல்",
    "telugu": "రిన్యూవల్",
    "malayalam": "റിന്യൂവൽ",
    "bengali": "রিনিউয়াল",
    "gujarati": "રીન્યુઅલ",
    "marathi": "रिन्यूअल"
  },
  "surrender": {
    "hindi": "सरेंडर",
    "tamil": "சரெண்டர்",
    "telugu": "సరెండర్",
    "malayalam": "സറണ്ടർ",
    "bengali": "সারেন্ডার",
    "gujarati": "સરેન્ડર",
    "marathi": "सरेंडर"
  },
  "payout": {
    "hindi": "पेयआउट",
    "tamil": "பேய்அவுட்",
    "telugu": "పేయౌట్",
    "malayalam": "പേയൗട്ട്",
    "bengali": "পেআউট",
    "gujarati": "પેઆઉટ",
    "marathi": "पेआउट"
  },

  "payouts": {
    "hindi": "पेयआउट्स",
    "tamil": "பேய்அவுட்ஸ்",
    "telugu": "పేయౌట్స్",
    "malayalam": "പേയൗട്ട്സ്",
    "bengali": "পেআউটস",
    "gujarati": "પેઆઉટ્સ",
    "marathi": "पेआउट्स"
  },
  "pension": {
    "hindi": "पेंशन",
    "tamil": "பென்ஷன்",
    "telugu": "పెన్షన్",
    "malayalam": "പെൻഷൻ",
    "bengali": "পেনশন",
    "gujarati": "પેન્શન",
    "marathi": "पेन्शन"
  },
  "maturity": {
    "hindi": "मैच्योरिटी",
    "tamil": "மேச்சூரிட்டி",
    "telugu": "మెచ్యూరిటీ",
    "malayalam": "മാച്ചുറിറ്റി",
    "bengali": "ম্যাচুরিটি",
    "gujarati": "મેચ્યુરિટી",
    "marathi": "मॅच्युरिटी"
  },
  "installment": {
    "hindi": "इंस्टॉलमेंट",
    "tamil": "இன்ஸ்டால்மெண்ட்",
    "telugu": "ఇన్‌స్టాల్‌మెంట్",
    "malayalam": "ഇൻസ്റ്റാൾമെന്റ്",
    "bengali": "ইনস্টলমেন্ট",
    "gujarati": "ઇન્સ્ટોલમેન્ટ",
    "marathi": "इन्स्टॉलमेंट"
  },
  "installments": {
    "hindi": "इंस्टॉलमेंट्स",
    "tamil": "இன்ஸ்டால்மெண்ட்ஸ்",
    "telugu": "ఇన్‌స్టాల్‌మెంట్స్",
    "malayalam": "ഇൻസ്റ്റാൾമെന്റ്സ്",
    "bengali": "ইনস্টলমেন্টস",
    "gujarati": "ઇન્સ્ટોલમેન્ટ્સ",
    "marathi": "इन्स्टॉलमेंट्स"
  },
  "discount": {
    "hindi": "डिस्काउंट",
    "tamil": "டிஸ்கவுண்ட்",
    "telugu": "డిస్కౌంట్",
    "malayalam": "ഡിസ്കൗണ്ട്",
    "bengali": "ডিসকাউন্ট",
    "gujarati": "ડિસ્કાઉન્ટ",
    "marathi": "डिस्काउंट"
  },
  "discounts": {
    "hindi": "डिस्काउंट्स",
    "tamil": "டிஸ்கவுண்ட்ஸ்",
    "telugu": "డిస్కౌంట్స్",
    "malayalam": "ഡിസ്കൗണ്ട്സ്",
    "bengali": "ডিসকাউন্টস",
    "gujarati": "ડિસ્કાઉન્ટ્સ",
    "marathi": "डिस्काउंट्स"
  },
  "receipt": {
    "hindi": "रसीद",
    "tamil": "ரசீது",
    "telugu": "రసీదు",
    "malayalam": "രസീത്",
    "bengali": "রসিদ",
    "gujarati": "રસીદ",
    "marathi": "पावती"
  },
  "security": {
    "hindi": "सिक्योरिटी",
    "tamil": "சிக்யூரிட்டி",
    "telugu": "సెక్యూరిటీ",
    "malayalam": "സെക്യൂരിറ്റി",
    "bengali": "সিকিউরিটি",
    "gujarati": "સિક્યોરિટી",
    "marathi": "सिक्युरिटी"
  },
  "stability": {
    "hindi": "स्टेबिलिटी",
    "tamil": "ஸ்டெபிலிட்டி",
    "telugu": "స్టెబిలిటీ",
    "malayalam": "സ്റ്റബിലിറ്റി",
    "bengali": "স্ট্যাবিলিটি",
    "gujarati": "સ્ટેબિલિટી",
    "marathi": "स्टॅबिलिटी"
  },
  "stock": {
    "hindi": "स्टॉक",
    "tamil": "ஸ்டாக்",
    "telugu": "స్టాక్",
    "malayalam": "സ്റ്റോക്ക്",
    "bengali": "স্টক",
    "gujarati": "સ્ટોક",
    "marathi": "स्टॉक"
  },
  "terminal": {
    "hindi": "टर्मिनल",
    "tamil": "டெர்மினல்",
    "telugu": "టెర్మినల్",
    "malayalam": "ടെർമിനൽ",
    "bengali": "টার্মিনাল",
    "gujarati": "ટર્મિનલ",
    "marathi": "टर्मिनल"
  },
  "terms": {
    "hindi": "टर्म्स",
    "tamil": "டெர்ம்ஸ்",
    "telugu": "టెర్మ్స్",
    "malayalam": "ടേംസ്",
    "bengali": "টার্মস",
    "gujarati": "ટર્મ્સ",
    "marathi": "टर्म्स"
  },
  "yield": {
    "hindi": "यील्ड",
    "tamil": "யீல்ட்",
    "telugu": "యీల్డ్",
    "malayalam": "യീൽഡ്",
    "bengali": "ইয়িল্ড",
    "gujarati": "યીલ્ડ",
    "marathi": "यील्ड"
  },
  "shield": {
    "hindi": "शील्ड",
    "tamil": "ஷீல்ட்",
    "telugu": "షీల్డ్",
    "malayalam": "ഷീൽഡ്",
    "bengali": "শিল্ড",
    "gujarati": "શીલ્ડ",
    "marathi": "शील्ड"
  },
  "sip": {
    "hindi": "एसआईपी",
    "tamil": "எஸ்ஐபி",
    "telugu": "ఎస్‌ఐపీ",
    "malayalam": "എസ്.ഐ.പി",
    "bengali": "এসআইপি",
    "gujarati": "એસઆઈપી",
    "marathi": "एसआयपी"
  },
  "solvency": {
    "hindi": "सॉल्वेंसी",
    "tamil": "சால்வென்சி",
    "telugu": "సాల్వెన్సీ",
    "malayalam": "സോൾവൻസി",
    "bengali": "সলভেন্সি",
    "gujarati": "સોલ્વન્સી",
    "marathi": "सॉल्व्हेन्सी"
  },

  "underwriting": {
    "hindi": "अंडरराइटिंग",
    "tamil": "அண்டர்ரைட்டிங்",
    "telugu": "అండర్‌రైటింగ్",
    "malayalam": "അണ്ടർറൈറ്റിംഗ്",
    "bengali": "আন্ডাররাইটিং",
    "gujarati": "અન્ડરરાઇટિંગ",
    "marathi": "अंडररायटिंग"
  },
  "valuation": {
    "hindi": "वैल्यूएशन",
    "tamil": "வால்யூயேஷன்",
    "telugu": "వాల్యూయేషన్",
    "malayalam": "വാല്യൂയേഷൻ",
    "bengali": "ভ্যালুয়েশন",
    "gujarati": "વેલ્યુએશન",
    "marathi": "व्हॅल्यूएशन"
  },
  "reserving": {
    "hindi": "रिज़र्विंग",
    "tamil": "ரிசர்விங்",
    "telugu": "రిజర్వింగ్",
    "malayalam": "റിസർവിംഗ്",
    "bengali": "রিজার্ভিং",
    "gujarati": "રિઝર્વિંગ",
    "marathi": "रिझर्व्हिंग"
  },
  "mortality": {
    "hindi": "मॉर्टेलिटी",
    "tamil": "மோர்டாலிட்டி",
    "telugu": "మోర్టాలిటీ",
    "malayalam": "മോർട്ടാലിറ്റി",
    "bengali": "মর্টালিটি",
    "gujarati": "મોર્ટાલિટી",
    "marathi": "मॉर्टॅलिटी"
  },
  "morbidity": {
    "hindi": "मॉर्बिडिटी",
    "tamil": "மோர்பிடிட்டி",
    "telugu": "మోర్బిడిటీ",
    "malayalam": "മോർബിഡിറ്റി",
    "bengali": "মরবিডিটি",
    "gujarati": "મોર્બિડિટી",
    "marathi": "मॉर्बिडिटी"
  },
  "frequency": {
    "hindi": "फ्रीक्वेंसी",
    "tamil": "ஃப்ரீக்வென்சி",
    "telugu": "ఫ్రీక్వెన్సీ",
    "malayalam": "ഫ്രീക്വൻസി",
    "bengali": "ফ্রিকোয়েন্সি",
    "gujarati": "ફ્રીક્વન્સી",
    "marathi": "फ्रिक्वेन्सी"
  },
  "severity": {
    "hindi": "सीवियरिटी",
    "tamil": "சீவெரிட்டி",
    "telugu": "సీవేరిటీ",
    "malayalam": "സീവിയറിറ്റി",
    "bengali": "সিভিয়ারিটি",
    "gujarati": "સીવિયરિટી",
    "marathi": "सीव्हियरिटी"
  },
  "exposure": {
    "hindi": "एक्सपोज़र",
    "tamil": "எக்ஸ்போஷர்",
    "telugu": "ఎక్స్‌పోజర్",
    "malayalam": "എക്സ്പോഷർ",
    "bengali": "এক্সপোজার",
    "gujarati": "એક્સપોઝર",
    "marathi": "एक्सपोजर"
  },
  "assumption": {
    "hindi": "असम्पशन",
    "tamil": "அசம்ப்ஷன்",
    "telugu": "అసంప్షన్",
    "malayalam": "അസംപ്ഷൻ",
    "bengali": "অ্যাসাম্পশন",
    "gujarati": "અસંપશન",
    "marathi": "असम्प्शन"
  },
  "interest rate assumption": {
    "hindi": "इंटरेस्ट रेट असम्पशन",
    "tamil": "இன்ட்ரஸ்ட் ரேட் அசம்ப்ஷன்",
    "telugu": "ఇంట్రెస్ట్ రేట్ అసంప్షన్",
    "malayalam": "ഇന്ററെസ്റ്റ് റേറ്റ് അസംപ്ഷൻ",
    "bengali": "ইন্টারেস্ট রেট অ্যাসাম্পশন",
    "gujarati": "ઇન્ટરેસ્ટ રેટ અસંપશન",
    "marathi": "इंटरेस्ट रेट असम्प्शन"
  },
  "lapse assumption": {
    "hindi": "लैप्स असम्पशन",
    "tamil": "லாப்ஸ் அசம்ப்ஷன்",
    "telugu": "లాప్స్ అసంప్షన్",
    "malayalam": "ലാപ്സ് അസംപ്ഷൻ",
    "bengali": "ল্যাপ্স অ্যাসাম্পশন",
    "gujarati": "લેપ્સ અસંપશન",
    "marathi": "लॅप्स असम्प्शन"
  },
  "persistency rate": {
    "hindi": "परसिस्टेंसी रेट",
    "tamil": "பர்சிஸ்டென்சி ரேட்",
    "telugu": "పర్సిస్టెన్సీ రేట్",
    "malayalam": "പേഴ്സിസ്റ്റൻസി റേറ്റ്",
    "bengali": "পারসিস্টেন্সি রেট",
    "gujarati": "પરસિસ્ટન્સી રેટ",
    "marathi": "परसिस्टन्सी रेट"
  },
  "risk margin": {
    "hindi": "रिस्क मार्जिन",
    "tamil": "ரிஸ்க் மார்ஜின்",
    "telugu": "రిస్క్ మార్జిన్",
    "malayalam": "റിസ്ക് മാർജിൻ",
    "bengali": "রিস্ক মার্জিন",
    "gujarati": "રિસ્ક માર્જિન",
    "marathi": "रिस्क मार्जिन"
  },
  "capital requirement": {
    "hindi": "कैपिटल रिक्वायरमेंट",
    "tamil": "கேப்பிடல் ரிக்வயர்மெண்ட்",
    "telugu": "క్యాపిటల్ రిక్వైర్‌మెంట్",
    "malayalam": "ക്യാപിറ്റൽ റിക്വയർമെന്റ്",
    "bengali": "ক্যাপিটাল রিকোয়ারমেন্ট",
    "gujarati": "કેપિટલ રિક્વાયરમેન્ટ",
    "marathi": "कॅपिटल रिक्वायरमेंट"
  },
  "solvency ratio": {
    "hindi": "सॉल्वेंसी रेशियो",
    "tamil": "சால்வென்சி ரேஷியோ",
    "telugu": "సాల్వెన్సీ రేషియో",
    "malayalam": "സോൾവൻസി റേഷ്യോ",
    "bengali": "সলভেন্সি রেশিও",
    "gujarati": "સોલ્વન્સી રેશિયો",
    "marathi": "सॉल्व्हेन्सी रेशियो"
  },
  
  "inflation": {
    "hindi": "इन्फ्लेशन",
    "tamil": "இன்ஃபிளேஷன்",
    "telugu": "ఇన్ఫ్లేషన్",
    "malayalam": "ഇൻഫ്ലേഷൻ",
    "bengali": "ইনফ্লেশন",
    "gujarati": "ઇન્ફ્લેશન",
    "marathi": "इन्फ्लेशन"
  },
  "deflation": {
    "hindi": "डिफ्लेशन",
    "tamil": "டிஃப்ளேஷன்",
    "telugu": "డిఫ్లేషన్",
    "malayalam": "ഡിഫ്ലേഷൻ",
    "bengali": "ডিফ্লেশন",
    "gujarati": "ડિફ્લેશન",
    "marathi": "डिफ्लेशन"
  },
  "margin": {
    "hindi": "मार्जिन",
    "tamil": "மார்ஜின்",
    "telugu": "మార్జిన్",
    "malayalam": "മാർജിൻ",
    "bengali": "মার্জিন",
    "gujarati": "માર્જિન",
    "marathi": "मार्जिन"
  },
  "dividend": {
    "hindi": "डिविडेंड",
    "tamil": "டிவிடெண்ட்",
    "telugu": "డివిడెండ్",
    "malayalam": "ഡിവിഡൻഡ്",
    "bengali": "ডিভিডেন্ড",
    "gujarati": "ડિવિડેન્ડ",
    "marathi": "डिव्हिडेंड"
  },
  "share": {
    "hindi": "शेयर",
    "tamil": "ஷேர்",
    "telugu": "షేర్",
    "malayalam": "ഷെയർ",
    "bengali": "শেয়ার",
    "gujarati": "શેર",
    "marathi": "शेअर"
  },
  "derivative": {
    "hindi": "डेरिवेटिव",
    "tamil": "டெரிவேட்டிவ்",
    "telugu": "డెరివేటివ్",
    "malayalam": "ഡെരിവേറ്റീവ്",
    "bengali": "ডেরিভেটিভ",
    "gujarati": "ડેરિવેટિવ",
    "marathi": "डेरिव्हेटिव्ह"
  },
  "swap": {
    "hindi": "स्वैप",
    "tamil": "ஸ்வாப்",
    "telugu": "స్వాప్",
    "malayalam": "സ്വാപ്പ്",
    "bengali": "সোয়াপ",
    "gujarati": "સ્વેપ",
    "marathi": "स्वॅप"
  },
  "commodity": {
    "hindi": "कमोडिटी",
    "tamil": "கமாடிட்டி",
    "telugu": "కమోడిటీ",
    "malayalam": "കമോഡിറ്റി",
    "bengali": "কমোডিটি",
    "gujarati": "કમોડિટી",
    "marathi": "कमोडिटी"
  },
  "treasury": {
    "hindi": "ट्रेज़री",
    "tamil": "ட்ரெஷரி",
    "telugu": "ట్రెజరీ",
    "malayalam": "ട്രഷറി",
    "bengali": "ট্রেজারি",
    "gujarati": "ટ્રેઝરી",
    "marathi": "ट्रेजरी"
  },
  "debt": {
    "hindi": "डेब्ट",
    "tamil": "டெப்ட்",
    "telugu": "డెబ్ట్",
    "malayalam": "ഡെബ്റ്റ്",
    "bengali": "ডেব্ট",
    "gujarati": "ડેબ્ટ",
    "marathi": "डेब्ट"
  },
  "principal": {
    "hindi": "प्रिंसिपल",
    "tamil": "பிரின்சிபல்",
    "telugu": "ప్రిన్సిపల్",
    "malayalam": "പ്രിൻസിപ്പൽ",
    "bengali": "প্রিন্সিপাল",
    "gujarati": "પ્રિન્સિપલ",
    "marathi": "प्रिन्सिपल"
  },
  "default": {
    "hindi": "डिफॉल्ट",
    "tamil": "டிஃபால்ட்",
    "telugu": "డిఫాల్ట్",
    "malayalam": "ഡിഫോൾട്ട്",
    "bengali": "ডিফল্ট",
    "gujarati": "ડિફોલ્ટ",
    "marathi": "डिफॉल्ट"
  },
  "amortization": {
    "hindi": "एमॉर्टाइज़ेशन",
    "tamil": "அமோர்டைசேஷன்",
    "telugu": "అమార్టైజేషన్",
    "malayalam": "അമോർട്ടൈസേഷൻ",
    "bengali": "অ্যামর্টাইজেশন",
    "gujarati": "એમોર્ટાઇઝેશન",
    "marathi": "अमॉर्टायझेशन"
  },
  "leverage": {
    "hindi": "लेवरेज",
    "tamil": "லெவரேஜ்",
    "telugu": "లెవరేజ్",
    "malayalam": "ലെവറേജ്",
    "bengali": "লেভারেজ",
    "gujarati": "લેવરેજ",
    "marathi": "लेव्हरेज"
  },
  "hedge": {
    "hindi": "हेज",
    "tamil": "ஹெட்ஜ்",
    "telugu": "హెడ్జ్",
    "malayalam": "ഹെഡ്ജ്",
    "bengali": "হেজ",
    "gujarati": "હેજ",
    "marathi": "हेज"
  },
  
  "liquidity": {
    "hindi": "लिक्विडिटी",
    "tamil": "லிக்விடிட்டி",
    "telugu": "లిక్విడిటీ",
    "malayalam": "ലിക്വിഡിറ്റി",
    "bengali": "লিকুইডিটি",
    "gujarati": "લિક્વિડિટી",
    "marathi": "लिक्विडिटी"
  },
  "volatility": {
    "hindi": "वोलैटिलिटी",
    "tamil": "வாலட்டிலிட்டி",
    "telugu": "వోలాటిలిటీ",
    "malayalam": "വോളട്ടിലിറ്റി",
    "bengali": "ভোলাটিলিটি",
    "gujarati": "વોલેટિલિટી",
    "marathi": "व्होलॅटिलिटी"
  },
  "benchmark": {
    "hindi": "बेंचमार्क",
    "tamil": "பெஞ்ச்மார்க்",
    "telugu": "బెంచ్‌మార్క్",
    "malayalam": "ബെഞ്ച്മാർക്ക്",
    "bengali": "বেঞ্চমার্ক",
    "gujarati": "બેન્ચમાર્ક",
    "marathi": "बेंचमार्क"
  },
  "portfolio": {
    "hindi": "पोर्टफोलियो",
    "tamil": "போர்ட்ஃபோலியோ",
    "telugu": "పోర్ట్‌ఫోలియో",
    "malayalam": "പോർട്ട്ഫോളിയോ",
    "bengali": "পোর্টফোলিও",
    "gujarati": "પોર્ટફોલિયો",
    "marathi": "पोर्टफोलिओ"
  },
  "allocation": {
    "hindi": "एलोकेशन",
    "tamil": "அலோகேஷன்",
    "telugu": "అలోకేషన్",
    "malayalam": "അലോക്കേഷൻ",
    "bengali": "অ্যালোকেশন",
    "gujarati": "એલોકેશન",
    "marathi": "अलोकेशन"
  },
  "diversification": {
    "hindi": "डाइवर्सिफिकेशन",
    "tamil": "டைவர்சிபிகேஷன்",
    "telugu": "డైవర్సిఫికేషన్",
    "malayalam": "ഡൈവേഴ്സിഫിക്കേഷൻ",
    "bengali": "ডাইভার্সিফিকেশন",
    "gujarati": "ડાયવર્સિફિકેશન",
    "marathi": "डायव्हर्सिफिकेशन"
  },
  "exposure": {
    "hindi": "एक्सपोज़र",
    "tamil": "எக்ஸ்போஷர்",
    "telugu": "ఎక్స్‌పోజర్",
    "malayalam": "എക്സ്പോഷർ",
    "bengali": "এক্সপোজার",
    "gujarati": "એક્સપોઝર",
    "marathi": "एक्सपोजर"
  },
  "correlation": {
    "hindi": "कोरिलेशन",
    "tamil": "கோரிலேஷன்",
    "telugu": "కోరిలేషన్",
    "malayalam": "കൊറിലേഷൻ",
    "bengali": "কোরিলেশন",
    "gujarati": "કોરિલેશન",
    "marathi": "कोरिलेशन"
  },
  "valuation": {
    "hindi": "वैल्यूएशन",
    "tamil": "வால்யூவேஷன்",
    "telugu": "వాల్యుయేషన్",
    "malayalam": "വാല്യുവേഷൻ",
    "bengali": "ভ্যালুয়েশন",
    "gujarati": "વેલ્યુએશન",
    "marathi": "व्हॅल्यूएशन"
  },
  "yield": {
    "hindi": "यील्ड",
    "tamil": "யீல்ட்",
    "telugu": "యీల్డ్",
    "malayalam": "യീൽഡ്",
    "bengali": "ইয়িল্ড",
    "gujarati": "યીલ્ડ",
    "marathi": "यिल्ड"
  },
  "coupon": {
    "hindi": "कूपन",
    "tamil": "கூப்பன்",
    "telugu": "కూపన్",
    "malayalam": "കൂപ്പൺ",
    "bengali": "কুপন",
    "gujarati": "કૂપન",
    "marathi": "कूपन"
  },
  "maturity": {
    "hindi": "मैच्योरिटी",
    "tamil": "மேச்சூரிட்டி",
    "telugu": "మెచ్యూరిటీ",
    "malayalam": "മാച്ചുറിറ്റി",
    "bengali": "ম্যাচুরিটি",
    "gujarati": "મેચ્યુરિટી",
    "marathi": "मॅच्युरिटी"
  },
  "settlement": {
    "hindi": "सेटलमेंट",
    "tamil": "செட்டில்மெண்ட்",
    "telugu": "సెట్టిల్‌మెంట్",
    "malayalam": "സെറ്റിൽമെന്റ്",
    "bengali": "সেটেলমেন্ট",
    "gujarati": "સેટલમેન્ટ",
    "marathi": "सेटलमेंट"
  },
  "clearing": {
    "hindi": "क्लियरिंग",
    "tamil": "க்ளியரிங்",
    "telugu": "క్లియరింగ్",
    "malayalam": "ക്ലിയറിംഗ്",
    "bengali": "ক্লিয়ারিং",
    "gujarati": "ક્લિયરિંગ",
    "marathi": "क्लिअरिंग"
  },
  "custodian": {
    "hindi": "कस्टोडियन",
    "tamil": "கஸ்டோடியன்",
    "telugu": "కస్టోడియన్",
    "malayalam": "കസ്റ്റോഡിയൻ",
    "bengali": "কাস্টডিয়ান",
    "gujarati": "કસ્ટોડિયન",
    "marathi": "कस्टोडियन"
  },
  
  "brokerage": {
    "hindi": "ब्रोकरेज",
    "tamil": "ப்ரோகரேஜ்",
    "telugu": "బ్రోకరేజ్",
    "malayalam": "ബ്രോക്കറേജ്",
    "bengali": "ব্রোকারেজ",
    "gujarati": "બ્રોકરેજ",
    "marathi": "ब्रोकरेज"
  },
  "commission": {
    "hindi": "कमीशन",
    "tamil": "கமிஷன்",
    "telugu": "కమిషన్",
    "malayalam": "കമ്മീഷൻ",
    "bengali": "কমিশন",
    "gujarati": "કમિશન",
    "marathi": "कमिशन"
  },
  "spread": {
    "hindi": "स्प्रेड",
    "tamil": "ஸ்ப்ரெட்",
    "telugu": "స్ప్రెడ్",
    "malayalam": "സ്പ്രെഡ്",
    "bengali": "স্প্রেড",
    "gujarati": "સ્પ્રેડ",
    "marathi": "स्प्रेड"
  },
  "interest": {
    "tamil": "இன்ட்ரஸ்ட்",
    "telugu": "ఇంట్రెస్ట్",
    "malayalam": "ഇന്ററസ്റ്റ്",
    "bengali": "ইন্টারেস্ট",
    "gujarati": "ઇન્ટરેસ્ટ",
    "marathi": "इंटरेस्ट"
  },
  "deflation": {
    "tamil": "டிஃப்ளேஷன்",
    "telugu": "డిఫ్లేషన్",
    "malayalam": "ഡിഫ്ലേഷൻ",
    "bengali": "ডিফ্লেশন",
    "gujarati": "ડિફ્લેશન",
    "marathi": "डिफ्लेशन"
  },
  "margin": {
    "tamil": "மார்ஜின்",
    "telugu": "మార్జిన్",
    "malayalam": "മാർജിൻ",
    "bengali": "মার্জিন",
    "gujarati": "માર્જિન",
    "marathi": "मार्जिन"
  },
  "dividend": {
    "tamil": "டிவிடெண்ட்",
    "telugu": "డివిడెండ్",
    "malayalam": "ഡിവിഡൻഡ്",
    "bengali": "ডিভিডেন্ড",
    "gujarati": "ડિવિડેન્ડ",
    "marathi": "डिविडेंड"
  },
  "share": {
    "tamil": "ஷேர்",
    "telugu": "షేర్",
    "malayalam": "ഷെയർ",
    "bengali": "শেয়ার",
    "gujarati": "શેર",
    "marathi": "शेअर"
  },
  "derivative": {
    "tamil": "டெரிவேட்டிவ்",
    "telugu": "డెరివేటివ్",
    "malayalam": "ഡെറിവേറ്റീവ്",
    "bengali": "ডেরিভেটিভ",
    "gujarati": "ડેરિવેટિવ",
    "marathi": "डेरिवेटिव्ह"
  },
  "swap": {
    "tamil": "ஸ்வாப்",
    "telugu": "స్వాప్",
    "malayalam": "സ്വാപ്പ്",
    "bengali": "সোয়াপ",
    "gujarati": "સ્વાપ",
    "marathi": "स्वॅप"
  },
  "commodity": {
    "tamil": "கமாடிட்டி",
    "telugu": "కమోడిటీ",
    "malayalam": "കമോഡിറ്റി",
    "bengali": "কমোডিটি",
    "gujarati": "કોમોડિટી",
    "marathi": "कमोडिटी"
  },
  "treasury": {
    "tamil": "ட்ரெஷரி",
    "telugu": "ట్రెజరీ",
    "malayalam": "ട്രഷറി",
    "bengali": "ট্রেজারি",
    "gujarati": "ટ્રેઝરી",
    "marathi": "ट्रेझरी"
  },
  "debt": {
    "tamil": "டெப்ட்",
    "telugu": "డెబ్ట్",
    "malayalam": "ഡെബ്റ്റ്",
    "bengali": "ডেব্ট",
    "gujarati": "ડેબ્ટ",
    "marathi": "डेब्ट"
  },
  "principal": {
    "tamil": "பிரின்சிபல்",
    "telugu": "ప్రిన్సిపల్",
    "malayalam": "പ്രിൻസിപ്പൽ",
    "bengali": "প্রিন্সিপাল",
    "gujarati": "પ્રિન્સિપલ",
    "marathi": "प्रिन्सिपल"
  },
  "default": {
    "tamil": "டிஃபால்ட்",
    "telugu": "డిఫాల్ట్",
    "malayalam": "ഡിഫാൾട്ട്",
    "bengali": "ডিফল্ট",
    "gujarati": "ડિફોલ્ટ",
    "marathi": "डिफॉल्ट"
  },
  "amortization": {
    "tamil": "அமோர்டைசேஷன்",
    "telugu": "అమోర్టైజేషన్",
    "malayalam": "അമോർട്ടൈസേഷൻ",
    "bengali": "অ্যামর্টাইজেশন",
    "gujarati": "અમોર્ટાઇઝેશન",
    "marathi": "अमोर्टायझेशन"
  },
  "leverage": {
    "tamil": "லெவரேஜ்",
    "telugu": "లెవరేజ్",
    "malayalam": "ലെവറേജ്",
    "bengali": "লেভারেজ",
    "gujarati": "લેવરેજ",
    "marathi": "लेव्हरेज"
  },
  "hedge": {
    "tamil": "ஹெட்ஜ்",
    "telugu": "హెడ్జ్",
    "malayalam": "ഹെഡ്ജ്",
    "bengali": "হেজ",
    "gujarati": "હેજ",
    "marathi": "हेज"
  }
}


# ============================================================================
# KEEP_ORIGINAL_WORDS - Words That Should NOT Be Translated
# ============================================================================
# These words will remain in English even in translated documents
# Use for brand names, product names, acronyms, etc.

KEEP_ORIGINAL_WORDS = {


    # Technical terms & Acronyms
    "API", "URL", "HTTP", "HTTPS", "PDF", "JSON", "XML",
    "AI", "ML", "IoT", "SaaS", "SDK", "IDE",

    # Insurance Product Names
    "ace", "bajaj life", "gwg", "longlife", "nri", "supreme", "terminal",
    "atpd", "auto", "awg", "cr", "deposits", "gpb", "gpg", "gst",
    "health management", "hni", "india", "ipg", "irr", "isecure", "ulip",
    "life long goal", "market linked", "multipliers", "mwpa",
    "nominee", "nominees", "ppt", "premium holiday", "premium optional",
    "premium pay", "pt", "siso", "smoker", "spw", "superwoman",
    "rider", "safeguard", "critical illness", "suraksha", "swp", "care rider"
}

# ============================================================================
# LANGUAGE CODE MAPPING 
# ============================================================================

LANGUAGE_CODE_TO_DICT_KEY = {
    'hin_Deva': 'hindi',
    'tam_Taml': 'tamil',
    'tel_Telu': 'telugu',
    'mal_Mlym': 'malayalam',
    'ben_Beng': 'bengali',
    'guj_Gujr': 'gujarati',
    'mar_Deva': 'marathi',
    'pan_Guru': 'punjabi',
    'ory_Orya': 'odia',
    'asm_Beng': 'assamese',
}

# Create case-insensitive lookup dictionaries
TRANSLITERATE_WORDS_LOWER = {k.lower(): v for k, v in TRANSLITERATE_WORDS.items()}
KEEP_ORIGINAL_WORDS_LOWER = {word.lower() for word in KEEP_ORIGINAL_WORDS}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_transliteration(word: str, language_code: str) -> str:
    """
    Get the transliteration for a word in a specific language
    
    Args:
        word: English word to transliterate
        language_code: NLLB language code (e.g., 'hin_Deva', 'tam_Taml')
    
    Returns:
        Transliterated word or original word if not found
    """
    word_lower = word.lower().strip('.,!?;:()"\'')
    
    if word_lower not in TRANSLITERATE_WORDS_LOWER:
        return word
    
    # Get the language-specific dictionary key
    dict_key = LANGUAGE_CODE_TO_DICT_KEY.get(language_code, 'hindi')
    
    # Get the word variants dictionary
    word_variants = TRANSLITERATE_WORDS_LOWER[word_lower]
    
    # Return language-specific version, fallback to hindi
    return word_variants.get(dict_key, word_variants.get('hindi', word))


def should_keep_original(word: str) -> bool:
    """
    Check if a word should be kept in original (not translated)
    
    Args:
        word: Word to check
    
    Returns:
        True if word should remain in English, False otherwise
    """
    word_lower = word.lower().strip('.,!?;:()"\'')
    return word_lower in KEEP_ORIGINAL_WORDS_LOWER


def apply_translation_rules(original_text: str, translated_text: str, target_lang_code: str = None) -> str:
    """
    Apply transliteration and word preservation rules to translated text
    
    Args:   
        original_text: Original English text
        translated_text: Machine-translated text
        target_lang_code: NLLB language code (e.g., 'hin_Deva')
    
    Returns:
        Text with custom rules applied
    """
    # Default to Hindi if no language code provided
    if not target_lang_code:
        target_lang_code = 'hin_Deva'
    
    words_original = original_text.split()
    words_translated = translated_text.split()
    result_words = words_translated.copy()
    
    # Check each original word
    for i, word in enumerate(words_original):
        clean_word = word.strip('.,!?;:()"\'')
        
        # Rule 1: Keep original (don't translate)
        if should_keep_original(clean_word):
            if i < len(result_words):
                result_words[i] = word
            else:
                result_words.append(word)
        
        # Rule 2: Transliterate with language-specific version
        else:
            transliteration = get_transliteration(clean_word, target_lang_code)
            if transliteration != clean_word:  # Only replace if we found a transliteration
                # Preserve punctuation
                if word != clean_word:
                    punct = word[len(clean_word):]
                    transliteration = transliteration + punct
                
                if i < len(result_words):
                    result_words[i] = transliteration
                else:
                    result_words.append(transliteration)
    
    return ' '.join(result_words)
