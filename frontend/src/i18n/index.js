import React, { createContext, useContext, useEffect, useState, useCallback } from "react";

export const translations = {
  ar: {
    common: {
      appName: "CARGO", brandAr: "كارجو",
      login: "تسجيل الدخول", logout: "تسجيل الخروج", loading: "جارٍ التحميل...",
      save: "حفظ", cancel: "إلغاء", back: "رجوع", next: "التالي", confirm: "تأكيد",
      submit: "إرسال", edit: "تعديل", delete: "حذف", search: "بحث", home: "الرئيسية",
      profile: "الملف الشخصي", notifications: "الإشعارات", status: "الحالة", price: "السعر",
      currency: "ر.ع", date: "التاريخ", time: "الوقت", details: "التفاصيل", view: "عرض",
      close: "إغلاق", saveDraft: "حفظ كمسودة", publish: "نشر", none: "لا يوجد",
      required: "مطلوب", optional: "اختياري", km: "كم", from: "من", to: "إلى",
      accept: "قبول", reject: "رفض", all: "الكل", yes: "نعم", no: "لا", success: "تم بنجاح",
      error: "حدث خطأ", retry: "إعادة المحاولة", welcome: "مرحباً",
    },
    nav: {
      about: "من نحن", howItWorks: "كيف تعمل", services: "الخدمات", contact: "تواصل معنا",
      myShipments: "شحناتي", createShipment: "إنشاء شحنة", availableShipments: "الشحنات المتاحة",
      myBids: "عروضي", activeTrip: "الرحلة النشطة", completedTrips: "الرحلات المكتملة",
      dashboard: "لوحة التحكم", vehicle: "المركبة", documents: "المستندات", verification: "التوثيق",
      opportunities: "الفرص", offers: "العروض", drivers: "السائقون", vehicles: "المركبات",
      trips: "الرحلات", reports: "التقارير", users: "المستخدمون", shipments: "الشحنات",
      bids: "العروض", providers: "شركات النقل", customers: "العملاء", auditLog: "سجل التدقيق",
      operations: "مركز العمليات", settings: "الإعدادات", tracking: "التتبع",
    },
    landing: {
      heroTitle: "منصة النقل والشحن الرائدة في سلطنة عُمان والشرق الأوسط",
      heroSub: "نربط الشحنات بالسائقين وشركات النقل المناسبة من لحظة الطلب حتى التسليم",
      ctaPrimary: "ابدأ تجربة CARGO", ctaSecondary: "كيف تعمل CARGO",
      statShipments: "شحنة منجزة", statDrivers: "سائق نشط في عُمان", statResponse: "متوسط وقت الاستجابة",
      howTitle: "كيف تعمل CARGO", howSub: "ثلاث خطوات بسيطة من الطلب إلى التسليم",
      step1Title: "أنشئ شحنتك", step1Desc: "حدد التفاصيل وموقع الاستلام والتسليم على الخريطة",
      step2Title: "استقبل العروض", step2Desc: "قارن عروض السائقين وشركات النقل الموثقة واختر الأنسب",
      step3Title: "تتبع حتى التسليم", step3Desc: "تابع رحلتك لحظة بلحظة حتى تأكيد التسليم والتقييم",
      servicesTitle: "خدماتنا", servicesSub: "حلول نقل متكاملة لكل احتياجاتك اللوجستية",
      svcLand: "النقل البري", svcLandDesc: "شحن بري موثوق عبر جميع محافظات السلطنة",
      svcContainer: "نقل الحاويات", svcContainerDesc: "نقل الحاويات من وإلى الموانئ الرئيسية",
      svcFlatbed: "الشحنات المسطحة والثقيلة", svcFlatbedDesc: "معدات ثقيلة وشحنات كبيرة الحجم",
      svcExpress: "الشحن السريع", svcExpressDesc: "توصيل عاجل للشحنات الحساسة للوقت",
      whoTitle: "من يستخدم CARGO", customerCard: "العملاء", customerCardDesc: "أنشئ شحناتك واستقبل أفضل العروض",
      driverCard: "السائقون", driverCardDesc: "اعثر على شحنات قريبة منك وقدّم عروضك",
      providerCard: "شركات النقل", providerCardDesc: "أدر أسطولك وسائقيك من مكان واحد",
      contactTitle: "تواصل معنا", footerRights: "جميع الحقوق محفوظة",
      joinDriver: "انضم كسائق", joinCustomer: "ابدأ كعميل",
    },
    auth: {
      selectRole: "اختر نوع الحساب", customer: "عميل", driver: "سائق", provider: "شركة نقل",
      phone: "رقم الهاتف", phoneHint: "أدخل رقم هاتفك لاستلام رمز التحقق",
      name: "الاسم", sendOtp: "إرسال رمز التحقق", enterOtp: "أدخل رمز التحقق",
      otpSent: "تم إرسال رمز التحقق", verify: "تحقق ودخول", demoNote: "وضع تجريبي — رمزك هو:",
      resend: "إعادة الإرسال", changePhone: "تغيير الرقم",
      adminLogin: "دخول المسؤول", adminPortal: "بوابة الإدارة", email: "البريد الإلكتروني",
      password: "كلمة المرور", secureArea: "منطقة محمية — للمسؤولين المصرح لهم فقط",
      invalidCreds: "بيانات الدخول غير صحيحة",
    },
    shipment: {
      create: "إنشاء شحنة", title: "عنوان الشحنة", description: "وصف الشحنة",
      category: "فئة الشحنة", quantity: "الكمية", weight: "الوزن (كجم)", dimensions: "الأبعاد",
      images: "الصور", specialInstructions: "تعليمات خاصة", expectedPrice: "السعر المتوقع",
      pickupLocation: "موقع الاستلام", deliveryLocation: "موقع التسليم",
      confirmPickup: "تأكيد موقع الاستلام", confirmDelivery: "تأكيد موقع التسليم",
      searchLocation: "ابحث عن موقع...", selectedAddress: "العنوان المحدد",
      tapMapHint: "انقر على الخريطة لتحديد الموقع أو استخدم البحث", searchUnavailable: "تعذّر البحث حالياً — انقر على الخريطة لتحديد الموقع",
      pickupDate: "تاريخ الاستلام", deliveryDate: "تاريخ التسليم",
      vehicleType: "نوع المركبة", requiredCapacity: "السعة المطلوبة (طن)",
      loadingService: "خدمة التحميل", unloadingService: "خدمة التفريغ",
      schedule: "الجدول الزمني", additionalServices: "خدمات إضافية", review: "المراجعة",
      cargoDetails: "تفاصيل الشحنة", stepCargo: "التفاصيل", stepPickup: "الاستلام",
      stepDelivery: "التسليم", stepSchedule: "الجدولة", stepVehicle: "المركبة",
      stepReview: "المراجعة", noShipments: "لا توجد شحنات حالياً",
      createFirst: "أنشئ أول شحنة لك", createdSuccess: "تم إنشاء الشحنة بنجاح",
      publishedSuccess: "تم نشر الشحنة بنجاح", route: "المسار", bidsReceived: "العروض المستلمة",
      viewBids: "عرض العروض", noBidsYet: "لا توجد عروض بعد", missingPickup: "يرجى تحديد موقع الاستلام.",
      missingDelivery: "يرجى تحديد موقع التسليم.", missingBoth: "يرجى تحديد موقع الاستلام والتسليم.",
      titleRequired: "يرجى إدخال عنوان الشحنة", reviewNote: "راجع بيانات شحنتك قبل النشر",
      trackShipment: "تتبع الشحنة", confirmDeliveryBtn: "تأكيد استلام الشحنة",
      rateDriver: "قيّم السائق", vehiclePickup: "بيك أب", vehicleFlatbed: "شاحنة مسطحة",
      vehicleContainer: "شاحنة حاويات", vehicleRefrigerated: "شاحنة مبردة", vehicleTrailer: "مقطورة",
    },
    bid: {
      submit: "تقديم عرض", price: "قيمة العرض", note: "ملاحظة (اختياري)", submitted: "تم تقديم عرضك بنجاح",
      priceRequired: "يرجى إدخال سعر صحيح", accept: "قبول العرض", accepted: "تم قبول العرض",
      driver: "السائق", rating: "التقييم", completedTrips: "الرحلات المكتملة", verification: "التوثيق",
      compare: "مقارنة العروض", pending: "قيد الانتظار", won: "مقبول", lost: "غير مقبول",
      alreadyBid: "لقد قدمت عرضاً على هذه الشحنة", enterPrice: "أدخل قيمة عرضك بالريال العماني",
      notApproved: "يجب توثيق حسابك قبل المشاركة في العروض",
    },
    trip: {
      active: "الرحلة النشطة", noActive: "لا توجد رحلة نشطة حالياً", updateStatus: "تحديث الحالة",
      progress: "تقدم الرحلة", customer: "العميل", cargo: "الشحنة", currentStatus: "الحالة الحالية",
      contact: "الاتصال", startTrip: "بدء الرحلة", tracking: "التتبع", eta: "الوصول المتوقع",
      etaPlaceholder: "يُحسب لاحقاً", driverLocation: "موقع السائق", confirmedDelivery: "تم تأكيد التسليم",
      history: "سجل الرحلات", noHistory: "لا توجد رحلات مكتملة",
    },
    verification: {
      status: "حالة التوثيق", DRAFT: "مسودة", PENDING: "قيد الانتظار", UNDER_REVIEW: "قيد المراجعة",
      APPROVED: "موثّق", REJECTED: "مرفوض", SUSPENDED: "معلّق",
      submitDocs: "تقديم المستندات", drivingLicense: "رخصة القيادة", vehicleReg: "استمارة المركبة",
      insurance: "شهادة التأمين", expiry: "تاريخ الانتهاء", reference: "الرقم المرجعي",
      submitted: "تم تقديم المستندات للمراجعة", notApprovedBanner: "حسابك غير موثّق بعد — لا يمكنك تقديم العروض حتى تتم الموافقة",
      approvedBanner: "حسابك موثّق — يمكنك تصفح الشحنات وتقديم العروض",
      pendingBanner: "مستنداتك قيد المراجعة من قبل الإدارة",
    },
    admin: {
      dashboard: "لوحة القيادة", totalShipments: "إجمالي الشحنات", activeShipments: "الشحنات النشطة",
      completedShipments: "الشحنات المكتملة", activeTrips: "الرحلات النشطة", totalDrivers: "إجمالي السائقين",
      verifiedDrivers: "السائقون الموثقون", pendingVerification: "بانتظار التوثيق", providers: "شركات النقل",
      recentActivity: "النشاط الأخير", approve: "موافقة", reject: "رفض", suspend: "تعليق",
      requestChanges: "طلب تعديلات", reviewDocs: "مراجعة المستندات", noActivity: "لا يوجد نشاط",
      manageDrivers: "إدارة السائقين", driverApproved: "تمت الموافقة على السائق",
      driverRejected: "تم رفض السائق", driverSuspended: "تم تعليق السائق",
      adminNotes: "ملاحظات الإدارة", action: "الإجراء", entity: "الكيان", result: "النتيجة",
      timestamp: "الوقت", commandCenter: "مركز القيادة",
    },
    status: {
      DRAFT: "مسودة", PUBLISHED: "منشورة", BIDDING: "استقبال العروض", DRIVER_SELECTED: "تم اختيار السائق",
      PAYMENT_PENDING: "بانتظار الدفع", PAID: "مدفوعة", DRIVER_ASSIGNED: "تم تعيين السائق",
      DRIVER_EN_ROUTE: "السائق في الطريق", DRIVER_ARRIVED: "وصل السائق للاستلام", LOADING: "جارٍ التحميل",
      LOADED: "تم التحميل", IN_TRANSIT: "قيد النقل", NEAR_DESTINATION: "قرب الوجهة",
      DRIVER_ARRIVED_DESTINATION: "وصل السائق للوجهة", DELIVERED_PENDING_CONFIRMATION: "بانتظار تأكيد التسليم",
      DELIVERED: "تم التسليم", COMPLETED: "مكتملة", CANCELLED: "ملغاة", DISPUTED: "متنازع عليها", REFUNDED: "مستردة",
    },
    rating: {
      overall: "التقييم العام", serviceQuality: "جودة الخدمة", communication: "التواصل",
      onTime: "الالتزام بالوقت", comment: "تعليق", submit: "إرسال التقييم", thanks: "شكراً لتقييمك",
    },
    p11: {
      wiz: {
        whatShipment: "ما هي شحنتك؟", selectCategory: "اختر نوع الشحنة",
        whereShipment: "أين توجد شحنتك؟", whereDeliver: "إلى أين تريد نقل شحنتك؟",
        originHint: "الموقع الذي توجد فيه الشحنة حالياً وسيتم استلامها منه",
        destHint: "الوجهة التي تريد توصيل الشحنة إليها",
        weightUnit: "وحدة الوزن", packages: "عدد الطرود", fragile: "قابل للكسر",
        photos: "صور الشحنة", photosOptional: "اختياري — يمكنك إضافة عدة صور",
        addPhotos: "إضافة صور", city: "المدينة / المنطقة",
      },
      map: {
        useCurrent: "استخدام موقعي الحالي", locating: "جارٍ تحديد موقعك...",
        loading: "جارٍ تحميل الخريطة...", error: "تعذّر تحميل الخريطة", retry: "إعادة المحاولة",
        resolving: "جارٍ تحديد العنوان...", coordinates: "الإحداثيات",
        resolveError: "تعذّر تحديد اسم الموقع", unnamed: "موقع محدد على الخريطة",
      },
      doc: {
        myDocuments: "مستنداتي", driverDocs: "مستندات السائق", vehicleDocs: "مستندات المركبة",
        additionalDocs: "مستندات إضافية", upload: "رفع", uploaded: "تم الرفع", chooseFile: "اختر ملفاً",
        PENDING: "قيد المراجعة", APPROVED: "معتمد", REJECTED: "مرفوض", EXPIRED: "منتهي",
        required: "مطلوب", noExpiry: "بدون انتهاء", rejectionReason: "سبب الرفض",
        uploadHint: "ارفع صورة أو ملف PDF للمستند", notUploaded: "لم يُرفع بعد",
      },
      fin: {
        title: "المركز المالي", totalRevenue: "إجمالي الإيرادات", totalCommission: "إجمالي العمولات",
        driverEarnings: "أرباح السائقين", providerEarnings: "أرباح الشركات", refunds: "المستردات",
        adjustments: "التسويات", payouts: "المدفوعات", transactions: "المعاملات", balances: "الأرصدة",
        commission: "العمولة", commissionSettings: "إعدادات العمولة", commissionType: "نوع العمولة",
        commissionValue: "قيمة العمولة", currency: "العملة", percentage: "نسبة مئوية", fixed: "مبلغ ثابت",
        adjust: "تسوية", reason: "السبب", amount: "المبلغ", account: "الحساب", type: "النوع",
        gross: "الإجمالي", net: "الصافي", driverBalances: "أرصدة السائقين", providerBalances: "أرصدة الشركات",
        available: "الرصيد المتاح", earned: "المكتسب", noTransactions: "لا توجد معاملات",
        ledgerNote: "سجل مالي غير قابل للتعديل — التصحيحات تُضاف كمعاملات تسوية",
        txn_customer_payment: "دفعة عميل", txn_platform_commission: "عمولة المنصة",
        txn_driver_earning: "أرباح سائق", txn_provider_earning: "أرباح شركة", txn_adjustment: "تسوية",
        txn_refund: "استرداد", txn_payout: "دفعة",
      },
      rbac: {
        users: "المستخدمون الإداريون", roles: "الأدوار والصلاحيات", createAdmin: "إضافة مستخدم إداري",
        name: "الاسم", email: "البريد الإلكتروني", password: "كلمة المرور", role: "الدور",
        permissions: "الصلاحيات", assignRole: "تعيين الدور", create: "إنشاء", perms: "صلاحية",
      },
      docadmin: {
        title: "مراقبة المستندات", expiring: "قرب الانتهاء", expired: "منتهية", pending: "قيد المراجعة",
        owner: "المالك", flag: "الحالة", review: "مراجعة", ok: "سارية",
      },
      ops: {
        customers: "العملاء", activeDrivers: "سائقون نشطون", pendingDrivers: "بانتظار التوثيق",
        providers: "شركات النقل", activeShipments: "شحنات نشطة", biddingShipments: "شحنات في المزايدة",
        activeTrips: "رحلات نشطة", completedTrips: "رحلات مكتملة", cancelledShipments: "شحنات ملغاة",
        pendingDocuments: "مستندات معلقة", expiringDocuments: "مستندات قرب الانتهاء", pendingTransactions: "معاملات معلقة",
      },
    },
  },
  en: {
    common: {
      appName: "CARGO", brandAr: "كارجو",
      login: "Login", logout: "Logout", loading: "Loading...",
      save: "Save", cancel: "Cancel", back: "Back", next: "Next", confirm: "Confirm",
      submit: "Submit", edit: "Edit", delete: "Delete", search: "Search", home: "Home",
      profile: "Profile", notifications: "Notifications", status: "Status", price: "Price",
      currency: "OMR", date: "Date", time: "Time", details: "Details", view: "View",
      close: "Close", saveDraft: "Save Draft", publish: "Publish", none: "None",
      required: "Required", optional: "Optional", km: "km", from: "From", to: "To",
      accept: "Accept", reject: "Reject", all: "All", yes: "Yes", no: "No", success: "Success",
      error: "An error occurred", retry: "Retry", welcome: "Welcome",
    },
    nav: {
      about: "About", howItWorks: "How it Works", services: "Services", contact: "Contact",
      myShipments: "My Shipments", createShipment: "Create Shipment", availableShipments: "Available Shipments",
      myBids: "My Bids", activeTrip: "Active Trip", completedTrips: "Completed Trips",
      dashboard: "Dashboard", vehicle: "Vehicle", documents: "Documents", verification: "Verification",
      opportunities: "Opportunities", offers: "Offers", drivers: "Drivers", vehicles: "Vehicles",
      trips: "Trips", reports: "Reports", users: "Users", shipments: "Shipments",
      bids: "Bids", providers: "Providers", customers: "Customers", auditLog: "Audit Log",
      operations: "Operations Center", settings: "Settings", tracking: "Tracking",
    },
    landing: {
      heroTitle: "The leading transport & logistics platform in Oman and the Middle East",
      heroSub: "We connect shipments with the right drivers and carriers — from request to delivery",
      ctaPrimary: "Start with CARGO", ctaSecondary: "How CARGO works",
      statShipments: "Shipments completed", statDrivers: "Active drivers in Oman", statResponse: "Avg. response time",
      howTitle: "How CARGO works", howSub: "Three simple steps from request to delivery",
      step1Title: "Create your shipment", step1Desc: "Set details and pick locations on the map",
      step2Title: "Receive bids", step2Desc: "Compare verified driver & carrier bids and pick the best",
      step3Title: "Track to delivery", step3Desc: "Follow your trip live until confirmation and rating",
      servicesTitle: "Our Services", servicesSub: "End-to-end transport solutions for your logistics needs",
      svcLand: "Land Freight", svcLandDesc: "Reliable land transport across all governorates",
      svcContainer: "Container Trucking", svcContainerDesc: "Container haulage to and from major ports",
      svcFlatbed: "Flatbed & Heavy Haul", svcFlatbedDesc: "Heavy equipment and oversized cargo",
      svcExpress: "Express Cargo", svcExpressDesc: "Urgent delivery for time-sensitive shipments",
      whoTitle: "Who uses CARGO", customerCard: "Customers", customerCardDesc: "Create shipments and get the best bids",
      driverCard: "Drivers", driverCardDesc: "Find nearby loads and submit your bids",
      providerCard: "Carriers", providerCardDesc: "Manage your fleet and drivers in one place",
      contactTitle: "Contact Us", footerRights: "All rights reserved",
      joinDriver: "Join as Driver", joinCustomer: "Start as Customer",
    },
    auth: {
      selectRole: "Select account type", customer: "Customer", driver: "Driver", provider: "Carrier",
      phone: "Phone number", phoneHint: "Enter your phone to receive a verification code",
      name: "Name", sendOtp: "Send verification code", enterOtp: "Enter verification code",
      otpSent: "Verification code sent", verify: "Verify & Login", demoNote: "Demo mode — your code is:",
      resend: "Resend", changePhone: "Change number",
      adminLogin: "Admin Login", adminPortal: "Admin Portal", email: "Email",
      password: "Password", secureArea: "Restricted area — authorized administrators only",
      invalidCreds: "Invalid credentials",
    },
    shipment: {
      create: "Create Shipment", title: "Shipment title", description: "Cargo description",
      category: "Cargo category", quantity: "Quantity", weight: "Weight (kg)", dimensions: "Dimensions",
      images: "Images", specialInstructions: "Special instructions", expectedPrice: "Expected price",
      pickupLocation: "Pickup Location", deliveryLocation: "Delivery Location",
      confirmPickup: "Confirm Pickup Location", confirmDelivery: "Confirm Delivery Location",
      searchLocation: "Search for a location...", selectedAddress: "Selected address",
      tapMapHint: "Tap the map to set the location, or use search", searchUnavailable: "Search unavailable right now — tap the map to set the location",
      pickupDate: "Pickup date", deliveryDate: "Delivery date",
      vehicleType: "Vehicle type", requiredCapacity: "Required capacity (ton)",
      loadingService: "Loading service", unloadingService: "Unloading service",
      schedule: "Schedule", additionalServices: "Additional services", review: "Review",
      cargoDetails: "Cargo Details", stepCargo: "Details", stepPickup: "Pickup",
      stepDelivery: "Delivery", stepSchedule: "Schedule", stepVehicle: "Vehicle",
      stepReview: "Review", noShipments: "No shipments available",
      createFirst: "Create your first shipment", createdSuccess: "Shipment created successfully",
      publishedSuccess: "Shipment published successfully", route: "Route", bidsReceived: "Bids received",
      viewBids: "View bids", noBidsYet: "No bids yet", missingPickup: "Please select the pickup location.",
      missingDelivery: "Please select the delivery location.", missingBoth: "Please select the pickup and delivery locations.",
      titleRequired: "Please enter a shipment title", reviewNote: "Review your shipment before publishing",
      trackShipment: "Track shipment", confirmDeliveryBtn: "Confirm delivery received",
      rateDriver: "Rate driver", vehiclePickup: "Pickup", vehicleFlatbed: "Flatbed",
      vehicleContainer: "Container", vehicleRefrigerated: "Refrigerated", vehicleTrailer: "Trailer",
    },
    bid: {
      submit: "Submit Bid", price: "Bid amount", note: "Note (optional)", submitted: "Your bid was submitted",
      priceRequired: "Please enter a valid price", accept: "Accept Bid", accepted: "Bid accepted",
      driver: "Driver", rating: "Rating", completedTrips: "Completed trips", verification: "Verification",
      compare: "Compare Bids", pending: "Pending", won: "Accepted", lost: "Not accepted",
      alreadyBid: "You already bid on this shipment", enterPrice: "Enter your bid amount in OMR",
      notApproved: "Your account must be verified before bidding",
    },
    trip: {
      active: "Active Trip", noActive: "No active trip right now", updateStatus: "Update Status",
      progress: "Trip progress", customer: "Customer", cargo: "Cargo", currentStatus: "Current status",
      contact: "Contact", startTrip: "Start Trip", tracking: "Tracking", eta: "Estimated arrival",
      etaPlaceholder: "Calculated later", driverLocation: "Driver location", confirmedDelivery: "Delivery confirmed",
      history: "Trip history", noHistory: "No completed trips",
    },
    verification: {
      status: "Verification status", DRAFT: "Draft", PENDING: "Pending", UNDER_REVIEW: "Under Review",
      APPROVED: "Approved", REJECTED: "Rejected", SUSPENDED: "Suspended",
      submitDocs: "Submit Documents", drivingLicense: "Driving License", vehicleReg: "Vehicle Registration",
      insurance: "Insurance Certificate", expiry: "Expiry date", reference: "Reference number",
      submitted: "Documents submitted for review", notApprovedBanner: "Your account is not verified yet — you can't submit bids until approved",
      approvedBanner: "Your account is verified — you can browse shipments and submit bids",
      pendingBanner: "Your documents are under review by the administration",
    },
    admin: {
      dashboard: "Dashboard", totalShipments: "Total Shipments", activeShipments: "Active Shipments",
      completedShipments: "Completed Shipments", activeTrips: "Active Trips", totalDrivers: "Total Drivers",
      verifiedDrivers: "Verified Drivers", pendingVerification: "Pending Verification", providers: "Carriers",
      recentActivity: "Recent Activity", approve: "Approve", reject: "Reject", suspend: "Suspend",
      requestChanges: "Request Changes", reviewDocs: "Review Documents", noActivity: "No activity",
      manageDrivers: "Manage Drivers", driverApproved: "Driver approved",
      driverRejected: "Driver rejected", driverSuspended: "Driver suspended",
      adminNotes: "Admin notes", action: "Action", entity: "Entity", result: "Result",
      timestamp: "Time", commandCenter: "Command Center",
    },
    status: {
      DRAFT: "Draft", PUBLISHED: "Published", BIDDING: "Bidding", DRIVER_SELECTED: "Driver Selected",
      PAYMENT_PENDING: "Payment Pending", PAID: "Paid", DRIVER_ASSIGNED: "Driver Assigned",
      DRIVER_EN_ROUTE: "Driver En Route", DRIVER_ARRIVED: "Arrived at Pickup", LOADING: "Loading",
      LOADED: "Loaded", IN_TRANSIT: "In Transit", NEAR_DESTINATION: "Near Destination",
      DRIVER_ARRIVED_DESTINATION: "Arrived at Destination", DELIVERED_PENDING_CONFIRMATION: "Pending Confirmation",
      DELIVERED: "Delivered", COMPLETED: "Completed", CANCELLED: "Cancelled", DISPUTED: "Disputed", REFUNDED: "Refunded",
    },
    rating: {
      overall: "Overall rating", serviceQuality: "Service quality", communication: "Communication",
      onTime: "On-time delivery", comment: "Comment", submit: "Submit rating", thanks: "Thanks for your rating",
    },
    p11: {
      wiz: {
        whatShipment: "What is your shipment?", selectCategory: "Select cargo type",
        whereShipment: "Where is your shipment?", whereDeliver: "Where should we deliver it?",
        originHint: "Where the shipment currently is and will be collected from",
        destHint: "The destination where the shipment needs to go",
        weightUnit: "Weight unit", packages: "Number of packages", fragile: "Fragile",
        photos: "Shipment Photos", photosOptional: "Optional — you can add multiple photos",
        addPhotos: "Add photos", city: "City / area",
      },
      map: {
        useCurrent: "Use my current location", locating: "Locating...",
        loading: "Loading map...", error: "Could not load map", retry: "Retry",
        resolving: "Resolving address...", coordinates: "Coordinates",
        resolveError: "Couldn't fetch the location name", unnamed: "Pinned map location",
      },
      doc: {
        myDocuments: "My Documents", driverDocs: "Driver Documents", vehicleDocs: "Vehicle Documents",
        additionalDocs: "Additional Documents", upload: "Upload", uploaded: "Uploaded", chooseFile: "Choose file",
        PENDING: "Pending Review", APPROVED: "Approved", REJECTED: "Rejected", EXPIRED: "Expired",
        required: "Required", noExpiry: "No expiry", rejectionReason: "Rejection reason",
        uploadHint: "Upload an image or PDF of the document", notUploaded: "Not uploaded yet",
      },
      fin: {
        title: "Financial Center", totalRevenue: "Total Revenue", totalCommission: "Total Commission",
        driverEarnings: "Driver Earnings", providerEarnings: "Provider Earnings", refunds: "Refunds",
        adjustments: "Adjustments", payouts: "Payouts", transactions: "Transactions", balances: "Balances",
        commission: "Commission", commissionSettings: "Commission Settings", commissionType: "Commission type",
        commissionValue: "Commission value", currency: "Currency", percentage: "Percentage", fixed: "Fixed fee",
        adjust: "Adjustment", reason: "Reason", amount: "Amount", account: "Account", type: "Type",
        gross: "Gross", net: "Net", driverBalances: "Driver Balances", providerBalances: "Provider Balances",
        available: "Available balance", earned: "Earned", noTransactions: "No transactions",
        ledgerNote: "Immutable ledger — corrections are recorded as adjustment transactions",
        txn_customer_payment: "Customer payment", txn_platform_commission: "Platform commission",
        txn_driver_earning: "Driver earning", txn_provider_earning: "Provider earning", txn_adjustment: "Adjustment",
        txn_refund: "Refund", txn_payout: "Payout",
      },
      rbac: {
        users: "Admin Users", roles: "Roles & Permissions", createAdmin: "Add admin user",
        name: "Name", email: "Email", password: "Password", role: "Role",
        permissions: "Permissions", assignRole: "Assign role", create: "Create", perms: "permissions",
      },
      docadmin: {
        title: "Document Monitoring", expiring: "Expiring soon", expired: "Expired", pending: "Pending review",
        owner: "Owner", flag: "Flag", review: "Review", ok: "Valid",
      },
      ops: {
        customers: "Customers", activeDrivers: "Active drivers", pendingDrivers: "Pending verification",
        providers: "Providers", activeShipments: "Active shipments", biddingShipments: "Bidding shipments",
        activeTrips: "Active trips", completedTrips: "Completed trips", cancelledShipments: "Cancelled shipments",
        pendingDocuments: "Pending documents", expiringDocuments: "Expiring documents", pendingTransactions: "Pending transactions",
      },
    },
  },
};

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(() => localStorage.getItem("cargo_lang") || "ar");

  const applyDir = useCallback((l) => {
    const dir = l === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = l;
    document.documentElement.dir = dir;
  }, []);

  useEffect(() => { applyDir(lang); }, [lang, applyDir]);

  const setLang = useCallback((l) => {
    localStorage.setItem("cargo_lang", l);
    setLangState(l);
  }, []);

  const t = useCallback((key) => {
    const parts = key.split(".");
    let cur = translations[lang];
    for (const p of parts) {
      if (cur == null) return key;
      cur = cur[p];
    }
    return cur == null ? key : cur;
  }, [lang]);

  const dir = lang === "ar" ? "rtl" : "ltr";
  return (
    <I18nContext.Provider value={{ lang, setLang, t, dir, isRTL: lang === "ar" }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
