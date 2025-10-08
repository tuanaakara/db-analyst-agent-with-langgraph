DB Analyst Agent with LangGraph

Bu proje, bir SQL veritabanı üzerinde doğal dil ile sorgulama yapabilen bir yapay zeka ajanıdır. LangChain'in LangGraph kütüphanesi kullanılarak, bir kullanıcı sorusunu analiz edip mantıklı adımlara bölen, bu adımları SQL sorgularına çevirip çalıştıran ve sonuçları sentezleyerek kullanıcıya anlaşılır bir cevap sunan otonom bir sistem oluşturulmuştur.

Uygulama, ölçeklenebilir bir mikroservis mimarisiyle tasarlanmıştır:

    Backend: Agent mantığını, LLM iletişimini ve veritabanı işlemlerini yürüten bir FastAPI servisi.

    Frontend: Kullanıcının agent ile sohbet etmesini sağlayan modern bir Gradio web arayüzü.

🚀 Mimarî

Proje, birbirinden tamamen bağımsız iki ana servisten oluşur ve bu servisler Docker Compose ile yönetilir.

    Backend Servisi (app/):

        FastAPI ile geliştirilmiştir.

        Google Gemini modelini kullanarak doğal dil işleme yapar.

        LangGraph ile çok adımlı düşünme ve planlama yeteneğine sahiptir.

        SQL araçlarını kullanarak veritabanını sorgular.

        Tüm analiz sürecini (plan, SQL, sonuç) frontend'e canlı olarak yayınlar (streaming).

    Frontend Servisi (frontend/):

        Gradio ile geliştirilmiştir.

        Backend servisinin varlığından başka bir şey bilmez.

        Kullanıcıdan gelen girdiyi backend'in API'sine gönderir.

        Backend'den gelen canlı veri akışını alıp kullanıcıya anlık olarak gösterir.

✨ Özellikler

    Doğal Dilden SQL'e: "En çok mesaj atan 3 kullanıcı kim?" gibi cümleleri SQL sorgularına çevirir.

    Çok Adımlı Düşünme: LangGraph sayesinde karmaşık soruları mantıksal adımlara bölerek çözebilir.

    Kendi Kendini Düzeltme: Hatalı bir SQL sorgusu oluşturduğunda, hatayı analiz edip sorguyu düzelterek tekrar deneyebilir.

    Canlı Akış (Streaming): Agent'ın ne düşündüğünü, hangi planı yaptığını ve hangi sorguyu çalıştırdığını anlık olarak arayüzde gösterir.

    Ölçeklenebilir Mimari: Docker Compose ile yönetilen backend ve frontend servisleri, yüksek trafik altında bağımsız olarak ölçeklendirilebilir.



db-analyst-agent-with-langgraph/
│
├── .dockerignore         # Docker imajına kopyalanmayacak dosyaları belirtir
├── .env                  # Gizli bilgiler (API anahtarı vb.)
├── .env.example          # .env dosyası için doldurulması gereken şablon
├── .gitignore            # Git'e gönderilmeyecek dosyaları belirtir
├── docker-compose.yml    # Backend ve Frontend servislerini yöneten ana dosya
├── LICENSE               # Projenin lisans bilgileri (opsiyonel)
├── README.md             # Bu dosya
│
├── app/                  # <-- Backend Servisi
│   ├── Dockerfile          # Backend için Docker talimatları
│   ├── requirements.txt    # Backend'in Python bağımlılıkları
│   ├── backend.py          # FastAPI uygulamasının giriş noktası
│   ├── data/
│   │   └── .db # Veritabanı dosyası
│   └── db_analyst/
│       ├── __init__.py     # Bu klasörün bir Python paketi olduğunu belirtir
│       ├── agent.py        # Ana AIAnalyst sınıfını ve ana akışı içerir
│       ├── config.py       # Merkezi, gizli olmayan ayarlar
│       ├── exceptions.py   # Projeye özel hata sınıfları
│       ├── gemini_service.py # Gemini LLM ile iletişimi yönetir
│       ├── graph.py        # LangGraph mimarisini (workflow) kurar
│       ├── nodes.py        # Agent'ın mantık adımlarını (planner, executor) içerir
│       ├── prompts.py      # Tüm prompt şablonları
│       ├── schemas.py      # Pydantic veri modelleri (API ve State)
│       ├── tools.py        # Veritabanı araçları (execute_sql)
│       └── utils.py        # Genel yardımcı fonksiyonlar
│
└── frontend/             # <-- Frontend Servisi
    ├── Dockerfile          # Frontend için Docker talimatları
    ├── requirements.txt    # Frontend'in Python bağımlılıkları
    └── frontend.py         # Gradio arayüzünün giriş noktası



🛠️ Kurulum ve Çalıştırma

Bu projeyi çalıştırmanın iki yolu vardır. Önerilen ve en kolay yöntem Docker kullanmaktır.
Gerekli Araçlar

    Git

    Docker

    Docker Compose

Yapılandırma

Projeyi çalıştırmadan önce, ortam değişkenlerini ayarlamanız gerekmektedir.

    Projenin ana dizininde bulunan .env.example dosyasını kopyalayarak .env adında yeni bir dosya oluşturun.

    Oluşturduğunuz .env dosyasını bir metin editörü ile açın.

    GOOGLE_API_KEY değişkeninin karşısına kendi Google AI Studio API anahtarınızı yapıştırın.

Yöntem 1: Docker ile (Önerilen)

Bu yöntem, tüm bağımlılıkları ve servisleri izole konteynerler içinde çalıştırır.

    Projenin ana dizininde bir terminal açın.

    Aşağıdaki komutu çalıştırarak servisleri başlatın:

    docker-compose up --build

    Servisler başarıyla başladığında, web tarayıcınızı açın ve aşağıdaki adrese gidin:

        http://localhost:7860

Yöntem 2: Sanal Ortam (venv) ile (Docker olmadan)

Bu yöntem için iki ayrı terminal penceresine ihtiyacınız olacaktır.

    Genel Yapılandırma:

        Yukarıda anlatıldığı gibi .env dosyasını oluşturun ve GOOGLE_API_KEY'i ayarlayın.

        .env dosyasını açın ve BACKEND_URL değişkenini http://127.0.0.1:8000 olarak değiştirin.

    Terminal 1 (Backend'i çalıştırmak için):

    # Backend klasörüne git
    cd app

    # Sanal ortam oluştur ve aktive et
    python3 -m venv venv
    source venv/bin/activate

    # Bağımlılıkları kur
    pip install -r requirements.txt

    # Backend sunucusunu başlat
    uvicorn backend:app --reload

    Terminal 2 (Frontend'i çalıştırmak için):

    # Frontend klasörüne git
    cd frontend

    # Sanal ortam oluştur ve aktive et
    python3 -m venv venv
    source venv/bin/activate

    # Bağımlılıkları kur
    pip install -r requirements.txt

    # Frontend uygulamasını başlat
    python frontend.py

    Web tarayıcınızı açın ve http://localhost:7860 adresine gidin.

💻 Teknoloji Stack'i

    Backend: Python, FastAPI, LangChain, LangGraph, Google Gemini

    Frontend: Gradio, Requests

    Containerization: Docker, Docker Compose

    Veritabanı: SQLite (örnek veri için)