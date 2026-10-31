<template>
<div id="header-wrap">
    <div id="krds-skip-link"><a href="#contents">본문 바로가기</a></div>
    <div id="krds-masthead">
        <div class="toggle-wrap">
            <div class="toggle-head">
                <div class="inner">
                    <span class="nuri-txt">이 누리집은 대한민국 공식 전자정부 누리집입니다.</span>
                </div>
            </div>
        </div>
    </div>
    <header id="krds-header">
        <div class="header-in">
            <div class="header-container">
                <div class="inner">
                    <div class="header-branding">
                        <h1 class="logo"><a href="/" rel="nosublink nofollow" title="메인페이지로 이동"><span
                                            class="sr-only">고향사랑e음 로고</span></a></h1>
                        <span style="margin-left: 10px;" v-if="isDevelopment">개발테스트</span>
                        <div class="header-actions">
                            <button type="button" class="btn-navi logout" v-if="!showLogin"
                                @click.prevent="logout">로그아웃</button>
                            <button type="button" class="btn-navi login" v-else-if="showLogin"
                                @click.prevent="goLogin">로그인</button>
                            <button type="button" class="btn-navi join" v-if="showLogin"
                                @click="goToJoinPageBefore">회원가입</button>
                            <button type="button" class="btn-navi my" @click="getMyPage">마이페이지</button>
                            <button type="button" class="btn-navi basket" @click="openPresent">장바구니</button>
                            <button type="button" class="btn-navi confirm" @click="getMyReceipt">기부확인증</button>
                            <button type="button" class="btn-navi all" aria-controls="mobile-nav"
                                @click="mobileMenuOpen"><span class="sr-only">전체메뉴</span></button>
                        </div>
                    </div>
                </div>
            </div>
            <nav class="krds-main-menu">
                <div class="inner">
                    <ul class="gnb-menu" aria-label="메인 메뉴">
                        <li v-for="(item, index) in menuItems" :key="index">
                            <button
                                v-if="item.subFlag"
                                class="gnb-main-trigger"
                                :class="{ active : activeMainIndex === index }"
                                @click="toggleMainMenu(index)"
                                @keydown="mainMenuKeyNav"
                                data-trigger=""
                                :aria-expanded="activeMainIndex === index" aria-haspopup="true"
                                :aria-controls="`main-menu-${index}`"
                            >{{ item.mainMenu }}</button>
                            <button
                                v-else
                                 class="gnb-main-trigger"
                                @click="noSubMainMenu(index, item.subMenu[0].contents[0]);"
                                data-trigger=""
                                 :aria-controls="`main-menu-${index}`"
                            >{{ item.mainMenu }}</button>
                            <div v-if="item.subFlag" class="gnb-toggle-wrap" :id="`main-menu-${index}`"
                                :class="{ 'is-open' : activeMainIndex === index }">
                                <div class="gnb-main-list inner">
                                    <div class="gnb-sub-list single-list">
                                        <div class="gnb-sub-content" v-if="!item.gridChange">
                                            <ul class="type-description" v-if="item.subMenu.length <= 1">
                                                <li v-for="(subItem, subIndex) in item.subMenu[0].contents"
                                                    :key="subIndex">
                                                    <strong class="tit">
                                                        <a href="javascript:void(0)" @click="handleLocation(subItem)">{{
                                                            subItem.value }}</a>
                                                    </strong>
                                                    <p class="txt">{{ subItem.content }}</p>
                                                </li>
                                            </ul>
                                            <ul class="type-description" v-else-if="item.subMenu.length > 1">
                                                <li v-for="(subItem, subIndex) in item.subMenu" :key="subIndex">
                                                    <ul class="type-description--sub">
                                                        <li v-for="(subContents, subContentsIndex) in subItem.contents"
                                                            :key="subContentsIndex">
                                                            <strong class="tit">
                                                                <a href="javascript:void(0)"
                                                                    @click="handleLocation(subContents)">{{
                                                                    subContents.value }}</a>
                                                            </strong>
                                                            <p class="txt">{{ subContents.content }}</p>
                                                        </li>
                                                    </ul>
                                                </li>
                                            </ul>
                                        </div>
                                        <div v-else class="gnb-sub-content">
                                            <ul class="type-description grid-6">
                                                <li v-for="(subItem, subIndex) in item.subMenu" :key="subIndex">
                                                    <ul class="type-description--sub">
                                                        <li v-for="(subContents, subContentsIndex) in subItem.contents"
                                                            :key="subContentsIndex">
                                                            <strong class="tit" v-if="subContents.depth.length > 0">
                                                                <a href="javascript:void(0)" style="cursor: initial;">{{ subContents.value }}</a>
                                                            </strong>
                                                            <strong class="tit" v-else>
                                                                <a href="javascript:void(0)"
                                                                    @click="handleLocation(subContents)">{{
                                                                    subContents.value }}</a>
                                                            </strong>
                                                            <p class="txt">{{ subContents.content }}</p>
                                                            <ul v-if="subContents.depth.length > 0">
                                                                <li v-for="(depthItem, depthIndex) in subContents.depth" :key="depthIndex">
                                                                    <a href="javascript:void(0)" @click="handleLocation(depthItem);">
                                                                        {{ depthItem.value }}
                                                                    </a>
                                                                </li>
                                                            </ul>
                                                        </li>
                                                    </ul>
                                                </li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </li>
                    </ul>
                    <button type="button" class="gnb-all-btn open-modal" data-target="modal_sitemap"><span
                            class="sr-only">사이트맵</span></button>
                </div>
            </nav>
        </div>
        <nav id="mobile-nav" class="krds-main-menu-mobile" style="display: none;">
            <div class="gnb-wrap">
                <div class="gnb-header">
                    <div class="header-actions">
                        <button type="button" class="btn-navi navi-row my" @click="getMyPage">마이페이지</button>
                        <button type="button" class="btn-navi navi-row basket" @click="openPresent">장바구니</button>
                        <button type="button" class="btn-navi navi-row confirm" @click="getMyReceipt">기부확인증</button>
                    </div>
                </div>
                <div class="gnb-body">
                    <div class="gnb-bod__inner">
                        <total-give-state
                            @calc-modal-open="openCalc"
                        ></total-give-state>
                        <login-require v-if="!isLogin"></login-require>
                        <login-complete v-if="isLogin"></login-complete>
                    </div>
                    <div class="krds-accordion">
                        <div class="accordion-item" v-for="(item, index) in menuItems" :key="index"
                            :class="{ active : activeAccordionIndex === index }">
                            <div class="accordion-header">
                                <button type="button" class="btn-accordion"
                                    v-if="item.subFlag"
                                    :class="{ active : activeAccordionIndex === index }"
                                    :aria-expanded="activeAccordionIndex === index" aria-haspopup="true"
                                    :aria-controls="`accordion-${index}`" @click="toggleAccordionMenu(index)"
                                >{{ item.mainMenu }}</button>
                                <button type="button"
                                    v-else
                                    class="btn-accordion"
                                    :class="{ active : activeAccordionIndex === index }"
                                    @click="noSubAccordionMenu(index, item.subMenu[0].contents[0])"
                                >{{ item.mainMenu }}</button>
                            </div>
                            <div class="accordion-collapse" :id="`accordion-${index}`">
                                <div class="accordion-body" v-if="!item.gridChange">
                                    <ul class="gnb-mob" v-if="item.subMenu.length <= 1">
                                        <template v-for="subItem in item.subMenu">
                                            <li v-for="(subContents, subContentsIndex) in subItem.contents"
                                                :key="`${item.mainMenu}>${subContents.value}`">
                                                <a href="javascript:void(0)" @click="handleLocation(subContents)"
                                                    class="gnb-mob-menu">{{ subContents.value }}</a>
                                            </li>
                                        </template>
                                    </ul>
                                </div>
                                <div class="accordion-body" v-else>
                                    <ul class="gnb-mob">
                                        <template v-for="subItem in item.subMenu">
                                            <li 
                                                v-if="subContents.depth.length > 0"
                                                v-for="(subContents, subContentsIndex) in subItem.contents"
                                                :key="`${item.mainMenu}>${subContents.value}`">
                                                <a 
                                                    style="cursor: initial;"
                                                    href="javascript:void(0)"
                                                    class="gnb-mob-menu"
                                                >{{ subContents.value }}</a>
                                                <ul>
                                                    <li v-for="(depthItem, depthIndex) in subContents.depth" :key="`accordion-depth-${depthIndex}`">
                                                        <a                                             
                                                            href="javascript:void(0)"
                                                            @click="handleLocation(depthItem)"
                                                            class="gnb-mob-menu"
                                                        >{{ depthItem.value }}</a>
                                                    </li>
                                                </ul>
                                            </li>
                                            <li v-else
                                                v-for="(subContents, subContentsIndex) in subItem.contents"
                                                :key="`${item.mainMenu}>${subContents.value}>${subContentsIndex}`">
                                                <a                                             
                                                    href="javascript:void(0)"
                                                    @click="handleLocation(subContents)"
                                                    class="gnb-mob-menu"
                                                >{{ subContents.value }}</a>
                                            </lt>
                                        </template>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <button type="button" class="krds-btn medium icon" id="close-nav" @click="closeMainMenu()">
                    <span class="sr-only">전체메뉴 닫기</span>
                    <i class="svg-icon ico-popup-close"></i>
                </button>
            </div>
        </nav>
    </header>
    <modal-calc
        ref="modalCalc"
    ></modal-calc>
    <login-require-modal
        :is-open="isOpen"
    >
    </login-require-modal>
</div>
</template>
// 넷퍼넬 js
<script type="text/javascript" src="/static/js/netfunnel.js"></script>
<script type="text/javascript" src="/static/js/netfunnel_skin.js"></script>

// vue scripts
<script>
module.exports = {
    props: {
        isOpen: {
            type: Boolean,
            default: false
        }
    },
    components: {
        "total-give-state": httpVueLoader("/components/ui/total_give_state.vue"),
        "login-require": httpVueLoader("/components/ui/login-require.vue"),
        "login-complete": httpVueLoader("/components/ui/login-complete.vue"),
        "modal-calc": httpVueLoader("/components/ui/calc/modal-calc.vue"),
        "login-require-modal": httpVueLoader("/components/ui/login/login-require-modal.vue")
    },
    data: function() {
        return {
            isDevelopment: SERVER_POSITION == "development",
            isLogin: false,
            isGuestLogin: false,
            activeMainIndex:null,
            activeAccordionIndex:null,
            backdrop: null,
            _scrollY: 0,
            _scrollH: 0,
            _lastScrollY: 0,
            menuItems: [
                {
                    mainMenu: "기부하기",
                    subFlag: true,
                    gridChange: false,
                    subMenu: [
                        {
                            colInx: 1,
                            contents: [
                                {
                                    value: "기부하기",
                                    content: "내 고향에 직접 기부 할 수 있어요",
                                    url: "",
                                    func: $s.donation.goDonationPage,
                                    depth: []
                                },
                                {
                                    value: "특정사업 보러가기",
                                    content: "내 고향의 특정사업 목록을 볼 수 있어요",
                                    url: "/designated-donation/index.html",
                                    func: "",
                                    depth: []
                                }
                            ]
                        }
                    ]
                },
                {
                    mainMenu: "답례품",
                    subFlag: true,
                    gridChange: false,
                    subMenu: [
                        {
                            colInx: 1,
                            contents: [
                                {
                                    value: "답례품몰",
                                    content: "지역의 답례품을 확인 할 수 있어요",
                                    url: "/goods/index.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "마을기업관",
                                    content: "마을기업이 생산한 답례품들을 확인 할 수 있어요",
                                    url: "/community-business/communityList-main.html",
                                    func: "",
                                    depth: []
                                }
                            ]
                        }
                    ]
                },
                {
                    mainMenu: "사업안내",
                    subFlag: true,
                    gridChange: false,
                    subMenu: [
                        {
                            colInx: 1,
                            contents: [
                                {
                                    value: "자치단체 소개",
                                    content: "지역의 기금사업들을 볼 수 있어요",
                                    url: "/donation/list-select.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "고향사랑기부제 안내",
                                    content: "고향사랑기부제에 대해 확인할 수 있어요",
                                    url: "/donation/guide1.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "온라인 기부방법",
                                    content: "온라인 기부방법에 대해 확인할 수 있어요",
                                    url: "/donation/guide2.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "오프라인 기부방법",
                                    content: "오프라인 기부방법에 대해 확인할 수 있어요",
                                    url: "/donation/guide5.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "연말정산 세액공제 안내",
                                    content: "내가 기부한 기부금이 연말정산 때 어떻게 세액공제 되는지 확인 할 수 있어요",
                                    url: "/donation/guide3.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "고향사랑기부 주의사항",
                                    content: "고향사랑기부를 하기 전에 주의해야 할 사항을 확인할 수 있어요",
                                    url: "/donation/guide6.html",
                                    func: "",
                                    depth: []
                                }
                            ]
                        }
                    ]
                },
                {
                    mainMenu: "이벤트",
                    subFlag: false,
                    gridChange: false,
                    subMenu: [
                        {
                            colInx: 1,
                            contents: [
                                {
                                    value: "이벤트",
                                    content: "진행중인 이벤트를 확인할 수 있어요",
                                    url: "/featured/eventList.html?ing=Y",
                                    func: "",
                                    depth: []
                                }
                            ]
                        }
                    ]
                },
                {
                    mainMenu: "고객센터",
                    subFlag: true,
                    gridChange: false,
                    subMenu: [
                        {
                            colInx: 1,
                            contents: [
                                {
                                    value: "공지사항",
                                    content: "새소식, 운영점검 등 서비스 이용에 필요한 정보를 확인할 수 있어요",
                                    url: "/notice/list.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "자료실",
                                    content: "고향사랑e음 서비스 이용 관련 자료를 확인할 수 있어요",
                                    url: "/data-board/list.html",
                                    func: "",
                                    depth: []
                                },
                                {
                                    value: "FAQ",
                                    content: "가장 많이 질문 받은 내용을 FAQ 형식으로 확인할 수 있어요",
                                    url: "/faq/list.html",
                                    func: "",
                                    depth: []
                                }
                            ]
                        }
                    ]
                },
                {
                    mainMenu: "마이페이지",
                    subFlag: true,
                    gridChange: true,
                    subMenu: [
                        {
                            colInx: 1,
                            contents: [
                                {
                                    value: "기부내역 조회",
                                    content: "내가 기부한 내역을 확인할 수 있어요",
                                    url: "/mypage/cntrList.html",
                                    func: "",
                                    depth: []
                                }
                            ]
                        },
                        {
                            colInx: 2,
                            contents: [
                                {
                                    value: "주문 및 배송",
                                    content: "나의 주문내역을 조회할 수 있어요",
                                    url: "",
                                    func: this.getOrderList,
                                    depth: [
                                        {
                                            value: "주문·배송 조회",
                                            content: "내가 담은 답례품을 확인할 수 있어요",
                                            url: "",
                                            func: this.getOrderList
                                        },
                                        {
                                            value: "장바구니",
                                            content: "내가 담은 답례품을 확인할 수 있어요",
                                            url: "",
                                            func: this.openPresent
                                        },
                                    ]
                                },
                                {
                                    value: "취소·반품·교환",
                                    content: "나의 취소반품교환내역을 확인할 수 있어요",
                                    url: "/mypage/orderCancel.html",
                                    func: "",
                                    depth: []
                                }
                            ]
                        },
                        {
                            colInx: 3,
                            contents: [
                                {
                                    value: "기부증명서",
                                    content: "내가 기부한 내역을 확인할 수 있어요",
                                    url: "",
                                    func: this.getMyReceipt,
                                    depth: [
                                        {
                                            value: "기부확인증 보기",
                                            content: "내가 기부한 내역을 확인할 수 있어요",
                                            url: "",
                                            func: this.getMyReceipt,                    
                                        },
                                        {
                                            value: "기부혜택증 보기",
                                            content: "내가 기부한 고향에서 제공하는 혜택을 확인할 수 있어요",
                                            url: "/mypage/honorList.html",
                                            func: "",
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            colInx: 4,
                            contents: [
                                {
                                    value: "나의 활동",
                                    content: "내가 기부한 내역을 확인할 수 있어요",
                                    url: "",
                                    func: "",
                                    depth: [
                                        {
                                            value: "답례품 Q&A",
                                            content: "답례품에 대해 궁금한 사항에 대한 상담을 받을 수 있어요",
                                            url: "/mypage/inquiryItem.html",
                                            func: "",
                                        },
                                        {
                                            value: "답례품 후기",
                                            content: "내가 남긴 답례품 후기를 확인할 수 있어요",
                                            url: "/mypage/review.html",
                                            func: "",
                                        },
                                        {
                                            value: "1:1 문의",
                                            content: "고향사랑e음 이용 중 궁금한 사항에 대한 상담을 받을 수 있어요",
                                            url: "/mypage/inquiry.html",
                                            func: "",                            
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            colInx: 5,
                            contents: [
                                {
                                    value: "나의 관심",
                                    content: "내가 관심있는 내역을 확인할 수 있어요",
                                    url: "/mypage/intrstLocGov.html",
                                    func: "",
                                    colnum: 5,
                                    depth: []
                                }
                            ]
                        },
                        {
                            colInx: 6,
                            contents: [
                                {
                                    value: "나의 정보관리",
                                    content: "내가 관심있는 내역을 확인할 수 있어요",
                                    url: "/mypage/inquiry.html",
                                    func: "",
                                    colnum: 5,
                                    depth: [
                                        {
                                            value: "회원정보 수정",
                                            content: "나의 회원정보를 수정할 수 있어요",
                                            url: "/users/modify.html",
                                            func: "",
                                        },
                                        {
			    							value : "배송지 관리"
			    							,content : "나의 배송지를 관리할 수 있어요"
			    							,url : "/mypage/deliveryInfo.html"
			    							,func : ""
			    						},
                                        {
                                            value: "회원탈퇴",
                                            content: "회원탈퇴를 할 수 있어요",
                                            url: "/users/secede.html",
                                            func: "",
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    },

    // ******************************************************************** Computed *********************************************************************
    computed: {
        showLogin: function () {
	        return !(this.isLogin || this.isGuestLogin);
	    },
    },

    // ********************************************************************* Method **********************************************************************
    methods: {
        // 로그아웃
        logout: function () {
	        $s.logout();
      	},

        // 로그인
        goLogin: function () {
            $s.redirect($s.pages.LOGIN + "?target=" + encodeURIComponent($s.requestContext.requestFullUri)); // 로그인 후 로그인 진입 전 화면으로 이동하도록 수정
        },

        // 회원가입입
        goToJoinPageBefore: function () {
	        if ($s.config.isUseNetFunnel) {
	            NetFunnel_Action({ action_id: "join" }, function (ev, ret) {
	                location.href = "/users/join.html";
                });
	       } else {
	            location.href = "/users/join.html";
	       }
  		},

        // 마이페이지 이동
        getMyPage: function () {
            this.isLogin = $s.isLogin();
            if (this.isLogin) {
                location.href = "/mypage/index.html";
            } else {
                this.redirect($s.pages.LOGIN + "?target=" + "/mypage/index.html");
            }
 	    },

        // 장바구니
        openPresent: function () {
      	    this.isLogin = $s.isLogin();
 	        if (this.isLogin) {
	            $s.redirect("/cart/index.html");
            } else {
                $s.redirect($s.pages.LOGIN + "?target=" + "/cart/index.html");
            }
	    },

        // 기부확인증
        getMyReceipt: function () {
            this.isLogin = $s.isLogin();
 	      	if (this.isLogin) {
 	        	sessionStorage.setItem("receiptFromType","main");
 	         	location.href = "/mypage/receiptList.html";
            } else {
                this.redirect($s.pages.LOGIN + "?target=" + "/mypage/receiptList.html");
 	        }
        },

        // 주문조회
        getOrderList: function () {
            this.isLogin = $s.isLogin();
            if (this.isLogin) {
                location.href = "/mypage/orderList.html";
            } else {
                this.redirect($s.pages.LOGIN + "?target=" + "/mypage/orderList.html");
            }
        },

        // 메뉴 페이지 이동동
        handleLocation: function(menuItem){
            if(menuItem.url){
                window.location.href = menuItem.url;
            }else if (typeof menuItem.func === 'function'){
                menuItem.func();
            }else{;
                $s.alert("서비스 오픈예정 입니다.");
            }
        },

        // 포커스 트랩 설정정
        focusTrap: function(trap) {
 		    const focusableElements = trap.querySelectorAll(`a, button, [tabindex="0"], input, textarea, select`);
 		    if (!focusableElements.length) return;

 		    const firstFocusableElement = focusableElements[0];
 		    const lastFocusableElement = focusableElements[focusableElements.length - 1];

 		    trap.addEventListener("keydown", (event) => {
                if (event.key === "Tab") {
                    if (event.shiftKey && document.activeElement === firstFocusableElement) {
                        event.preventDefault();
                        lastFocusableElement.focus();
                    } else if (!event.shiftKey && document.activeElement === lastFocusableElement) {
                        event.preventDefault();
                        firstFocusableElement.focus();
                        // 모달 오픈 후 첫 초점 역방향 제어(modal-content가 첫초점이 아니면 사용 안해도 됨)
                    } else if (event.key === "Tab" && event.shiftKey && document.activeElement === trap) {
                        event.preventDefault();
                        lastFocusableElement.focus();
                    }
                }
 		    });
        },

        /* ================== PC 버전 ================== */
        // PC 버전 초기화
        krds_mainMenuPC_init : function(){
		    // dimed 요소를 설정, 기존 dimed가 없을 경우 생성
		    this.backdrop = document.querySelector(".gnb-backdrop") || this.createBackdrop();

		    // krds-main-menu 외부 클릭시 닫기
		    document.addEventListener("click", ({ target }) => {
		        if (!target.closest(".krds-main-menu")) this.toggleMainMenu(null);
		    });

		    // ESC 키를 눌러 메뉴를 닫거나, TAB 키로 초점이 메뉴 외부로 이동했을 때 메뉴 닫기
		    document.addEventListener("keyup", (event) => {
                if (event.code === "Escape" || !event.target.closest(".krds-main-menu")) {
                    this.toggleMainMenu(null);
                }
		    });
        },
        
        // 메인메뉴컨트롤
        toggleMainMenu: function(index){
            //기존 index와 클릭되는 index를 비교하여 toggle
            this.activeMainIndex = this.activeMainIndex === index ? null : index;
            //document 컨트롤영역
            const isOpen = this.activeMainIndex !== null;
            //메뉴활성화.
            this.toggleBackdrop(isOpen);
            this.toggleScrollbar(isOpen);
            this.adjustSubMenuHeight(document.querySelector(".gnb-main-list"));
        },

        // 서브메뉴없는 메뉴컨트롤
        noSubMainMenu: function(index, contents){
            //기존 index와 클릭되는 index를 비교하여 toggle
            this.activeMainIndex = this.activeMainIndex === index ? null : index;
            //document 컨트롤영역
            const isOpen = this.activeMainIndex !== null;
            //메뉴활성화.
            this.toggleBackdrop(isOpen);
            this.toggleScrollbar(isOpen);
            this.adjustSubMenuHeight(document.querySelector(".gnb-main-list"));

            this.handleLocation(contents);
        },

        // document 컨트롤
        toggleBackdrop: function(isOpen){
            document.querySelector(".gnb-backdrop").classList.toggle("active", isOpen);
            document.body.classList.toggle("is-gnb-web", isOpen);
        },

        // 스크롤 클래스 요소 toggle
        toggleScrollbar: function(isEnabled) {
		    const isScrollNeeded = document.body.scrollHeight > window.innerHeight;
		    document.body.classList.toggle("hasScrollY", isEnabled && isScrollNeeded);
        },

        // 서브 메뉴 높이를 활성 메뉴에 맞춰 조정정
        adjustSubMenuHeight: function(target) {
		    const activeSubList = target.querySelector(".gnb-sub-list.active");
		    const height = activeSubList?.scrollHeight || 0;
		    target.style.minHeight = `${height}px`;
        },

        // 배경을 위한 div 생성
        createBackdrop: function() {
		    const backdrop = document.createElement("div");
		    backdrop.classList.add("gnb-backdrop");
		    document.body.appendChild(backdrop);
		    return backdrop;
        },

        // 메뉴 키 이벤트 (현재 오류있음 수정필요)
        mainMenuKeyNav: function(event){

    	    const findDataTrigger = (element) => {
                const ul = element.closest("li").parentNode;
                const sibilngs = [...ul.children];
                return sibilngs.map((li) => li.querySelector("[data-trigger]")).filter(Boolean);
            };

            const findFocusableElement = (element, direction) => {
 	            const sibling = direction === "next" ? "nextElementSibling" : "previousElementSibling";
 	            const parent = element.closest("li")?.[sibling];
 	            return parent ? parent.querySelector("[data-trigger]") : null;
 	        };

            const focusMenuItem = (element) => {
	 	    	if (element) {
	        	    element.focus();
                }
            };

    	    const mainTriggers = findDataTrigger(event.currentTarget);

            const target = event.target;

            switch (event.key) {
                case "Home":
                    event.preventDefault();
                    focusMenuItem(mainTriggers[0]);
                    break;
                case "End":
                    event.preventDefault();
                    focusMenuItem(mainTriggers[mainTriggers.length - 1]);
                    break;
                case "ArrowRight":
                case "ArrowDown":
                    event.preventDefault();
                    const nextElement = findFocusableElement(target, "next");
                    focusMenuItem(nextElement);
                    break;
                case "ArrowLeft":
                case "ArrowUp":
                    event.preventDefault();
                    const previousElement = findFocusableElement(target, "prev");
                    focusMenuItem(previousElement);
                    break;
                default:
                    break;
            }
        },
        /* ================== PC 버전 END ================== */
        /* ================== MOBILE 버전 ================== */
        // MOBILE 버전 초기화
        krds_mainMenuMobile_init : function(){
    	    const mobileGnb = document.querySelector(".krds-main-menu-mobile:not(.sample)");

    	    if (!mobileGnb) return;

    	    if (mobileGnb.classList.contains("is-open")) {
    	        this.openMainMenu(mobileGnb);
    	    } else {
    	        mobileGnb.style.display = "none";
    	    }
            
    	    // 반응형 처리
    	    window.addEventListener("resize", () => {
    	        const isPC = windowSize.getWinSize() === "pc";
    	        if (isPC) this.closeMainMenu();
    	    });
        },

        // MOBILE 전체 메뉴 클릭시 오픈 설정
        mobileMenuOpen : function(event){
            const id = event.currentTarget.getAttribute("aria-controls");
            const mobileGnb = document.getElementById(id);

            if (!mobileGnb.closest(".gnb-wrap")) {
                    this.openMainMenu();
                    mobileGnb.querySelector(".gnb-wrap").focus();
            }
        },

        // 모바일에서의 메뉴 활성화를 위한 function
        openMainMenu: function() {
            const mobileGnb = document.querySelector(".krds-main-menu-mobile:not(.sample)");
            const navContainer = mobileGnb.querySelector(".gnb-wrap");

            mobileGnb.style.display = "block";

            // active 메뉴로 스크롤 이동
   	        const activeTrigger = document.querySelector(".gnb-main-trigger.active");
            if (activeTrigger) {
                const id = activeTrigger.getAttribute("aria-controls");
                const top = document.getElementById(id)?.offsetTop;
                const gnbBody = document.querySelector(".gnb-body");
                gnbBody.style.scrollBehavior = "auto";
                gnbBody.scrollTop = top;
            }

            setTimeout(() => {
                mobileGnb.classList.add("is-backdrop");
                mobileGnb.classList.add("is-open");
                document.body.classList.add("is-gnb-mobile");
            }, 100);

            const commponent = this;
            // transition 종료후 실행
            mobileGnb.addEventListener("transitionend", function onTransitionEnd() {
                navContainer.focus();
                mobileGnb.removeEventListener("transitionend", onTransitionEnd);

                // inert 설정
                document.querySelector("#krds-header .header-in").setAttribute("inert", "");
                document.getElementById("contents")?.setAttribute("inert", "");
                document.getElementById("krds-footer")?.setAttribute("inert", "");

                // 포커스 트랩 설정
                commponent.focusTrap(mobileGnb);
            });
   	    },

        // 메뉴 닫기
        closeMainMenu: function() {
   	        const mobileGnb = document.querySelector(".krds-main-menu-mobile:not(.sample)");
   	        const id = mobileGnb.getAttribute("id");
   	        const openGnb = document.querySelector(`[aria-controls=${id}]`);

	 	    mobileGnb.classList.remove("is-backdrop");
	 	    mobileGnb.classList.remove("is-open");

	 	    // inert 설정
		    document.querySelector("#krds-header .header-in").removeAttribute("inert");
		    document.getElementById("contents")?.removeAttribute("inert");
		    document.getElementById("krds-footer")?.removeAttribute("inert");

	 	    // transition 종료후 실행
	 	    mobileGnb.addEventListener("transitionend", function onTransitionEnd() {
	 	        openGnb.focus();
 		        mobileGnb.removeEventListener("transitionend", onTransitionEnd);
	 	    });

	 	    setTimeout(() => {
	 	        mobileGnb.style.display = "none";
	 	        document.body.classList.remove("is-gnb-mobile");
	 	    }, 400);
        },

        // 메인 메뉴컨트롤롤
        toggleAccordionMenu: function(index){
            this.activeAccordionIndex = this.activeAccordionIndex === index ? null : index;
        },

        // 서브메뉴없는 메뉴컨트롤
        noSubAccordionMenu: function(index, contents){
            this.handleLocation(contents);
        },
        /* ================== MOBILE 버전 END ================== */

        /* ================== 스크롤 이벤트  ================== */
        initScrollEvent: function(){
		  	window.addEventListener("scroll", () => {
                this.updateScrollValues();
                this.handleScrollDirection();
                this.closeMainMenu();
            });
        },

        // 스크롤 이벤트 적용
        updateScrollValues: function() {
		    this._scrollY = window.scrollY;
		    this._scrollH = document.body.scrollHeight;
        },

        handleScrollDirection: function() {
		    const $wrap = document.querySelector("#saleson");
		    if ($wrap) {
		      const _conOffsetTop = document.querySelector("#contents")?.offsetTop;
		      const _scrollY = window.scrollY;
		      const _scrollDown = _scrollY > this._lastScrollY;
		      const _scrollUp = _scrollY < this._lastScrollY;

		      if (_scrollY > _conOffsetTop + 50 && _scrollDown) {
		            $wrap.classList.add("scroll-down");
		            $wrap.classList.remove("scroll-up");
		      } else if (_scrollY > _conOffsetTop + 50 && _scrollUp) {
		            $wrap.classList.add("scroll-up");
		            $wrap.classList.remove("scroll-down");
		      } else {
		            $wrap.classList.remove("scroll-down", "scroll-up");
		      }
		        this._lastScrollY = _scrollY;
		    }
        },
        openCalc: function () {
            this.$refs.modalCalc.init();
            const modalElement = document.querySelector('.calcModal');
            const modal = new bootstrap.Modal(modalElement);

            modal.show();
        },
    },

    mounted: function() {
        this.isLogin = $s.isLogin();
        this.isGuestLogin = $s.isGuestLogin();

        // 초기 메뉴 초기화.
	  	this.krds_mainMenuPC_init()

	  	//모바일 전체메뉴 초기화.
	  	this.krds_mainMenuMobile_init();

        //스크롤에 대한 이벤트.
        this.initScrollEvent();
    },
};
</script>