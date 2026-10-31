/* 모바일 : 전체메뉴 */
const mobGnb = {
  target: {
    header       : "#header",
    gnbOpen      : "#m-gnb-open",
    gnbWrap      : ".m-gnb-wrap",
    gnbIn        : ".m-gnb-wrap .m-gnb-in",
    gnbBody      : ".m-gnb-wrap .m-gnb-body",
    gnbMenu      : ".m-gnb-wrap .menu-wrap .mn",
    gnbMenuHori  : ".m-gnb-wrap .menu-hori",
    gnbClose     : ".m-gnb-wrap .ico-close",
    gnbAnchor    : ".m-gnb-menu .submenu-wrap .dl",
    gnbTopScroll : ".m-gnb-wrap .m-gnb-top-scroll"
  },

  init: () => {
    const $mGnbBtn = document.querySelector(mobGnb.target.gnbOpen);
    const $mGnb = document.querySelector(mobGnb.target.gnbWrap);
    if (!$mGnb) return;

    const $mGnbCloseBtn = $mGnb.querySelector(mobGnb.target.gnbClose);
    const $mGnbBody = $mGnb.querySelector(mobGnb.target.gnbBody);

    mobGnb.anchor();
    mobGnb.accordion(); // ✅ 아코디언 여기서 1번만

    $mGnb.setAttribute("aria-hidden", "true");

    $mGnbBtn.addEventListener("click", mobGnb.open);
    $mGnbCloseBtn.addEventListener("click", mobGnb.close);
    $mGnbBody.addEventListener("scroll", mobGnb.anchorScroll);
  },

  open: () => {
    const $header = document.querySelector(mobGnb.target.header);
    const $mGnb = document.querySelector(mobGnb.target.gnbWrap);
    const $mGnbIn = document.querySelector(mobGnb.target.gnbIn);

    $header.style.zIndex = "1000";
    $mGnb.setAttribute("aria-hidden", "false");
    $mGnb.classList.add("is-open");
    $mGnbIn.setAttribute("tabindex", "0");
    $mGnbIn.focus();
    document.body.classList.add("is-m-gnb");
  },

  close: () => {
    const $header = document.querySelector(mobGnb.target.header);
    const $mGnb = document.querySelector(mobGnb.target.gnbWrap);
    const $mGnbBtn = document.querySelector(mobGnb.target.gnbOpen);
    const $mGnbIn = document.querySelector(mobGnb.target.gnbIn);

    $mGnb.classList.remove("is-open");
    $mGnb.classList.add("is-close");
    $mGnbIn.removeAttribute("tabindex");
    $mGnb.setAttribute("aria-hidden", "true");
    document.body.classList.remove("is-m-gnb");
    $mGnbBtn.focus();

    setTimeout(() => {
      $mGnb.classList.remove("is-close");
      $header.style.zIndex = "";
    }, 500);
  },

  /* 모바일 GNB 2뎁스 아코디언 */
  accordion: () => {
    if (mobGnb._accordionBinded) return;
    mobGnb._accordionBinded = true;

    document.addEventListener("click", (e) => {
      const $btn = e.target.closest(".sub-depth-trigger");
      if (!$btn) return;

      const $mGnb = $btn.closest(".m-gnb-wrap");
      if (!$mGnb) return;

      const isExpanded = $btn.getAttribute("aria-expanded") === "true";
      const targetId = $btn.getAttribute("aria-controls");
      const $subMenu = document.getElementById(targetId);
      if (!$subMenu) return;

      $btn.setAttribute("aria-expanded", String(!isExpanded));
      $subMenu.classList.toggle("is-open", !isExpanded);
    });
  },

  anchormenuReset: () => {
    document.querySelectorAll(mobGnb.target.gnbMenu)
      .forEach(el => el.classList.remove("active"));
  },

  anchor: () => {
    const $mGnb = document.querySelector(mobGnb.target.gnbWrap);
    if (!$mGnb) return;

    const $menus = $mGnb.querySelectorAll(mobGnb.target.gnbMenu);
    const $anchors = $mGnb.querySelectorAll(mobGnb.target.gnbAnchor);

    if ($menus.length) $menus[0].classList.add("active");

    $anchors.forEach($item => {
      $item.querySelectorAll(".is-depth4").forEach($btn => {
        $btn.addEventListener("click", (e) => {
          const $target = e.target.nextElementSibling;
          if (!$target) return;

          $target.style.display = "block";
          requestAnimationFrame(() => $target.classList.add("is-open"));
        });
      });
    });
  },

 anchorScroll: () => {
        const $mGnb = document.querySelector(mobGnb.target.gnbWrap);
        const $mGnbIn = $mGnb.querySelector(mobGnb.target.gnbIn);
        const $mGnbMenuHori = $mGnb.querySelector(mobGnb.target.gnbMenuHori);
        const $mGnbBody = $mGnb.querySelector(mobGnb.target.gnbBody);
        const $mGnbAnchors = $mGnb.querySelectorAll(mobGnb.target.gnbAnchor);
        const $mGnbTopScroll = $mGnb.querySelector(mobGnb.target.gnbTopScroll);
        const _scrollTop = $mGnbBody.scrollTop;
        const _scrollH = $mGnbBody.scrollHeight;
        const _bodyH = $mGnbBody.clientHeight;


        const reversedAnchors = Array.from($mGnbAnchors).reverse();

        reversedAnchors.forEach(($item) => {
            const _id = $item.getAttribute("id");
            const $mn = $mGnb.querySelector(`[href="#${_id}"]`);
            const _offset = $item.offsetTop;
            const isTargetReached = _scrollTop >= _offset;
            return;
            const isAtBottom = (_bodyH + _scrollTop >= _scrollH);
            if (isTargetReached) {
                mobGnb.anchormenuReset();
                $mn.classList.add("active");
                if($mGnbTopScroll) {
                    const $mGnbMenuHoriUl = $mGnbMenuHori.querySelector(".ul");
                    const _offsetLeft = $mn.offsetLeft;
                    $mGnbBody.addEventListener('scrollend', () => {
                        $mGnbMenuHoriUl.scrollLeft = _offsetLeft;
                    });
                }
            }
        });

        //gnb type2
        if($mGnbTopScroll) {
            let _lastBodyScrollY = 0;
            $mGnbBody.addEventListener('scroll', (e) => {
                const _bodyScrollY =  e.target.scrollTop;
                if (_bodyScrollY > 0) {
                    const _mGnbMenuScrollH = $mGnbTopScroll.scrollHeight;
                    $mGnbTopScroll.style.height = `${_mGnbMenuScrollH}px`;
                    $mGnbTopScroll.style.transition = "ease-out .4s";
                    $mGnbIn.classList.add("is-active");
                } else if (_bodyScrollY < 50 && _bodyScrollY < _lastBodyScrollY) {
                    $mGnbTopScroll.style.height = "";
                    $mGnbTopScroll.style.transition = "ease-out .4s .2s";
                    setTimeout(() => {
                        $mGnbIn.classList.remove("is-active");
                    }, 600);
                }
                _lastBodyScrollY = _bodyScrollY;
            });
        }
    },
};
document.addEventListener("DOMContentLoaded", () => {
  mobGnb.init();
});


/*** * 웹 gnb * ***/
const krds_pcGnb = {
	init() {
	  const gnbMenu = document.querySelector(".krds-gnb .gnb-menu");
	  if (!gnbMenu) return;

	  // gnb 속성설정
	  gnbMenu.setAttribute("aria-label", "메인 메뉴");
	  //gnbMenu.setAttribute("role", "menubar");

	  // li 요소 role 초기화
	  gnbMenu.querySelectorAll("li").forEach((li) => li.setAttribute("role", "none"));

	  // backdrop 설정
	  this.backdrop = document.querySelector(".gnb-backdrop") || this.createBackdrop();

	  // trigger 설정 및 이벤트 등록
	  const mainTriggers = gnbMenu.querySelectorAll(".gnb-main-trigger");
	  const subTriggers = gnbMenu.querySelectorAll(".gnb-sub-trigger");
	  mainTriggers.forEach((mainTrigger) => this.setupMainTrigger(mainTrigger));

	  this.addEvent(mainTriggers, subTriggers);
	  this.addKeyboardNavigation(mainTriggers);
	},
	setupMainTrigger(mainTrigger) {
	  const toggleWrap = mainTrigger.nextElementSibling;
	  if (toggleWrap) {
		//const uniqueIdx = `gnb-main-menu-${Math.random().toString(36).substring(2, 9)}`;
		const uniqueIdx = `gnb-main-menu-${crypto.randomUUID().replace(/-/g, '').slice(0,7)}`;
		//mainTrigger.setAttribute("role", "menuitem");
		mainTrigger.setAttribute("aria-controls", uniqueIdx);
		mainTrigger.setAttribute("aria-expanded", "false");
		//mainTrigger.setAttribute("aria-haspopup", "true");
		toggleWrap.setAttribute("id", uniqueIdx);
		//toggleWrap.setAttribute("role", "menu");

		const mainList = toggleWrap.querySelector(".gnb-main-list");
		if (mainList?.getAttribute("data-has-submenu") === "true") {
		  const subTriggers = mainList.querySelectorAll(".gnb-sub-trigger");
		  if (subTriggers.length > 0) {
			subTriggers[0].classList.add("active");
			subTriggers[0].nextElementSibling?.classList.add("active");
		  }
		  subTriggers.forEach((subTrigger) => this.setupSubTrigger(subTrigger));
		}
	  }
	},
	setupSubTrigger(subTrigger) {
	  const hasMenu = subTrigger.nextElementSibling;
	  if (hasMenu) {
		//const uniqueIdx = `gnb-sub-menu-${Math.random().toString(36).substring(2, 9)}`;
		const uniqueIdx = `gnb-main-menu-${crypto.randomUUID().replace(/-/g, '').slice(0,7)}`;
		//subTrigger.setAttribute("role", "menuitem");
		subTrigger.setAttribute("aria-controls", uniqueIdx);
		subTrigger.setAttribute("aria-expanded", subTrigger.classList.contains("active")?"true":"false");
		//subTrigger.setAttribute("aria-haspopup", "true");
		if(subTrigger.classList.contains("active")){
		  subTrigger.setAttribute("style", "border-left: solid;");
		}
		//hasMenu.setAttribute("role", "menu");
		hasMenu.setAttribute("id", uniqueIdx);
	  }
	},
	toggleMainMenu(mainTrigger) {
	  const isActive = mainTrigger.classList.contains("active");
	  const lang = document.documentElement.lang;
	  this.menuReset();
	  if (!isActive && mainTrigger.nextElementSibling) {
		mainTrigger.setAttribute("aria-expanded", "true");
		if(lang == 'en'){
		  mainTrigger.setAttribute("title", "Close Menu");
		}else{
		  mainTrigger.setAttribute("title", "메뉴 닫기");
		}
		mainTrigger.classList.add("active");
		mainTrigger.nextElementSibling.classList.add("is-open");
		this.toggleBackdrop(true);
		this.scrollbar(true);
		this.adjustSubMenuHeight(mainTrigger.nextElementSibling.querySelector(".gnb-main-list"));
		//this.attr('title', '펼치기');
	  } else {
		this.close();
		//this.attr('title', '접기');
	  }
	},
	toggleSubMenu(subTrigger) {
	  const otherSubTriggers = subTrigger.closest("ul").querySelectorAll(".gnb-sub-trigger");
	  otherSubTriggers.forEach((trigger) => {
		trigger.classList.remove("active");
		trigger.setAttribute("aria-expanded", "false");
		trigger.nextElementSibling?.classList.remove("active");
		trigger.removeAttribute("style");
	  });
	  subTrigger.classList.add("active");
	  subTrigger.setAttribute("aria-expanded", "true");
	  subTrigger.nextElementSibling?.classList.add("active");
	  subTrigger.setAttribute("style", "border-left: solid;");
	  this.adjustSubMenuHeight(subTrigger.closest(".gnb-main-list"));
	},
	createBackdrop() {
	  const backdrop = document.createElement("div");
	  backdrop.classList.add("gnb-backdrop");
	  backdrop.style.display = "none";
	  document.body.appendChild(backdrop);
	  return backdrop;
	},
	toggleBackdrop(isOpen) {
	  this.backdrop.style.display = isOpen ? "block" : "none";
	  document.body.classList.toggle("is-gnb-web", isOpen);
	},
	adjustSubMenuHeight(target) {
	  const activeSubList = target.querySelector(".gnb-sub-list.active");
	  const height = activeSubList?.scrollHeight || 0;
	  target.style.minHeight = `${height}px`;
	},
	scrollbar(hasScroll) {
	  const condition = hasScroll === "open" ? document.body.scrollHeight > window.innerHeight : hasScroll;
	  document.body.classList.toggle("hasScrollY", condition);
	},
	menuReset() {
	  document.querySelectorAll(".krds-gnb .gnb-main-trigger:not(.is-link)").forEach((mainTrigger) => {
		mainTrigger.classList.remove("active");
		mainTrigger.setAttribute("aria-expanded", "false");
		const lang = document.documentElement.lang;
		if(lang == 'en'){
          mainTrigger.setAttribute("title", "Expand Menu");
        }else{
          mainTrigger.setAttribute("title", "메뉴 열기");
        }
	  });
	  document.querySelectorAll(".krds-gnb .gnb-toggle-wrap").forEach((toggleWrap) => {
		toggleWrap.classList.remove("is-open");
	  });
	},
	close() {
	  this.toggleBackdrop(false);
	  this.menuReset();
	  this.scrollbar(false);
	},
	addEvent(mainTriggers, subTriggers) {
	  this.backdrop.addEventListener("click", () => this.close());
	  window.addEventListener("keyup", (event) => {
		if (event.code === "Escape" || !event.target.closest(".krds-gnb")) {
		  this.close();
		}
	  });
	  mainTriggers.forEach((mainTrigger) => {
		mainTrigger.addEventListener("click", () => this.toggleMainMenu(mainTrigger));
	  });
	  subTriggers.forEach((subTrigger) => {
		subTrigger.addEventListener("click", () => this.toggleSubMenu(subTrigger));
	  });
	},
	addKeyboardNavigation(mainTriggers) {
	  const focusMenuItem = (element) => {
		if (element) {
		  element.focus();
		}
	  };
	  const findFocusableElement = (element, direction) => {
		const sibling = direction === "next" ? "nextElementSibling" : "previousElementSibling";
		const parent = element.closest("li")?.[sibling];
		return parent ? parent.querySelector("[data-trigger]") : null;
	  };
	  document.addEventListener("keydown", (event) => {
		const target = event.target;
		if (target.getAttribute("data-trigger")) {
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
		}
	  });
	},
  };


/* 공통 : 레이아웃 */
const comLayout = {
    target: {
        headerTop : document.querySelector("#header-top"),
        header : document.querySelector("#header"),
        container : "#container",
        footer : "#footer",
    },

    init() {
        this.scroll();
        this.headerEvent();
        this.skipNav(); //
        window.addEventListener('resize', () => {
            this.headerEvent();
        });
    },

    skipNav() {
        const skipNav = document.querySelector('#skip-nav');
        const container = document.querySelector('#subContainer') || document.querySelector('#container');
        const header = document.querySelector('#header');

        if (!skipNav || !container || !header) return;

        skipNav.addEventListener('click', (e) => {
            e.preventDefault();

            const headerH = header.offsetHeight;
            const top =
                container.getBoundingClientRect().top +
                window.scrollY -
                headerH;

            window.scrollTo({
                top,
                behavior: 'auto'
            });

            // 포커스 보장 (접근성)
            container.setAttribute('tabindex', '0');
            container.focus({ preventScroll: true });
        });
    },

    scroll() {
        let _lastScrollY = 0;
        window.addEventListener('scroll', () => {
            const $wrap = document.querySelector("#wrap");
            const _conOffsetTop = document.querySelector("#container").offsetTop;
            const _scrollY = window.scrollY;

            if (_scrollY > _conOffsetTop + 50 && _scrollY > _lastScrollY) {
                $wrap.classList.add("scroll-down");
                $wrap.classList.remove("scroll-up");
            } else if (_scrollY > _conOffsetTop + 50 && _scrollY < _lastScrollY) {
                $wrap.classList.add("scroll-up");
                $wrap.classList.remove("scroll-down");
            } else {
                $wrap.classList.remove("scroll-down", "scroll-up");
            }

            _lastScrollY = _scrollY;
        });
    },

    headerEvent() {
        const $header = document.querySelector("#header");
        const _headerH = document.querySelector("#header .header-in").clientHeight;
        $header.style.height = `${_headerH + 1}px`;
    }
};


/* 공통 : 패턴 */
const common = {
    target: {
        header : document.querySelector("#header"),
        container : "#container",
        footer : "#footer",
        prefix : "krds",
    },
    device: {
        isMob : 1024,
    },
    init: ()=> {
        common.dropEvent ();
        common.toggleEvent();
        common.accordianEvent.init();
        const $links = document.querySelectorAll("a");
        $links.forEach($link => {
            const _href = $link.getAttribute( 'href' );
            $link.addEventListener("click", (el) => {
                if(_href === "#") el.preventDefault();
            });
        });
    },
    dropEvent: () => {
        const _dropBtns = document.querySelectorAll(`.${common.target.prefix}-drop-wrap .drop-btn`);

        _dropBtns.forEach(($dropBtn) => {
            const _span = document.createElement("span");
            const _txt = document.createTextNode("열기");
            _span.classList.add("sr-only");
            _span.appendChild(_txt);

            //$dropBtn.appendChild(_span);

            $dropBtn.addEventListener("click", ($el) => {
                const $menu = $el.target.nextElementSibling;
                const $srTxt = $el.target.querySelector(".sr-only");
                const lang = document.documentElement.lang;
                if($menu.style.display !== "block") {
                    common.dropClose();
                    $menu.style.display = "block"
                    $el.target.classList.add("active");

                    if($(event.target).parent().attr('class') == 'krds-drop-wrap zoom-drop'){
                       //$srTxt.textContent = "화면크기 닫기";
                       if(lang == 'en'){
                            $('#zoom').attr('title', 'Close');
                       }else{
                            $('#zoom').attr('title', '접기');
                       }
                    }else if($(event.target).parent().attr('class') == 'krds-drop-wrap'){
                       //$srTxt.textContent = "Language 닫기";
                       if(lang == 'en'){
                            $('#language').attr('title', 'Close');
                       }else{
                            $('#language').attr('title', '접기');
                       }
                    }else{
                       $srTxt.textContent = "닫기";
                    }
                } else {
                    common.dropClose();
                    if($(event.target).parent().attr('class') == 'krds-drop-wrap zoom-drop'){
                       //$srTxt.textContent = "화면크기 열기";
                       if(lang == 'en'){
                            $('#zoom').attr('title', 'Expand');
                       }else{
                            $('#zoom').attr('title', '열림');
                       }
                    }else if($(event.target).parent().attr('class') == 'krds-drop-wrap'){
                       //$srTxt.textContent = "Language 열기";
                       if(lang == 'en'){
                            $('#language').attr('title', 'Expand');
                       }else{
                            $('#language').attr('title', '열림');
                       }
                    }else{
                       $srTxt.textContent = "열기";
                    }
                }
            });
        });

        document.addEventListener("click", ($e) => {
            if(!$e.target.closest(`.${common.target.prefix}-drop-wrap`)) common.dropClose();
        });
    },
    dropClose: () => {
        const _dropBtns = document.querySelectorAll(`.${common.target.prefix}-drop-wrap .drop-btn`);
        const _dropMenus = document.querySelectorAll(`.${common.target.prefix}-drop-wrap .drop-menu`);
        _dropMenus.forEach(($menu) => {
            $menu.style.display = "";
        });
        _dropBtns.forEach(($btn) => {
            $btn.classList.remove("active");
        });
    },
    popupEvent: ($id) => {
        const $clickBtn = document.activeElement;
        const $header = common.target.header;
        const $openTarget = document.querySelector($id);
        const $openTargetType = $openTarget.getAttribute('data-type');
        const $focusPopupWrap = document.querySelector(`${$id}`);
        const $focusPopup = document.querySelector(`${$id} .popup`);
        const $closeBtn = document.querySelector(`${$id} .popup-close`);

        $openTarget.classList.add("is-open");

        document.body.classList.add("scroll-no");
        common.accEvent.open();
        if($openTargetType !== 'bottom' && common.target.header !== null) {
            $header.style.zIndex="1000";
        }

        if($openTargetType == 'full') {
            $openTarget.setAttribute("tabindex", 0);
            $focusPopupWrap.focus();
        } else {
            $focusPopup.setAttribute("tabindex", 0);
            $focusPopup.focus();
        }

        $closeBtn.addEventListener("click", () => {
            $openTarget.classList.remove("is-open");
            $openTarget.classList.add("is-close");
            $focusPopup.removeAttribute("tabindex");
            $clickBtn.focus();

            if (common.target.header !== null) $header.style.zIndex="";

            common.accEvent.close();
            setTimeout(() => {
                $openTarget.classList.remove("is-close");
                document.body.classList.remove("scroll-no");
            }, 600);
        });
    },
    accEvent :  {
        open : () => {
            const $container = document.querySelector(common.target.container);
            const $footer = document.querySelector(common.target.footer);
            $container.setAttribute("aria-hidden", "true");
            $footer.setAttribute("aria-hidden", "true");
        },
        close: () => {
            const $container = document.querySelector(common.target.container);
            const $footer = document.querySelector(common.target.footer);
            $container.setAttribute("aria-hidden", "false");
            $footer.setAttribute("aria-hidden", "false");
        },
    },
    toggleEvent : () => {
        const _toggleBtns = document.querySelectorAll(".toggle-btn");
        _toggleBtns.forEach(($toggleBtn) => {
            $toggleBtn.addEventListener("click", ($btnAct) => {
                const $target = $btnAct.target.closest(".toggle-head");
                const $targetBody = $target.nextElementSibling;
                const _targetBodyH = $targetBody.querySelector(".inner").scrollHeight;
                const $srEl = $btnAct.target.querySelector(".sr-only");

                if(!$target.classList.contains("active")) {
                    $srEl.innerText = '닫힘';
                    $target.classList.add("active");
                    $targetBody.classList.add("active");
                    $targetBody.style.height = `${_targetBodyH}px`;
                    window.addEventListener("resize", () => {
                        if($targetBody.classList.contains("active")) {
                            const _targetBodyH = $targetBody.querySelector(".inner").scrollHeight;
                            $targetBody.style.height = `${_targetBodyH }px`;
                        }
                    });
                } else {
                    $srEl.innerText = '열림';
                    $target.classList.remove("active");
                    $targetBody.classList.remove("active");
                    $targetBody.style.height = '';
                }

            })
        });
    },
    accordianEvent : {
        init: () => {
            const _accordians = document.querySelectorAll(".acco-list");
            _accordians.forEach(($parent) => {
                const _accoDataAct = $parent.getAttribute("data-action");
                const _accoAct = _accoDataAct !== null;
                const _lis = $parent.querySelectorAll(".li");
                const _list = [..._lis];
                _list.forEach(($e) => {
                    const $item = $e.closest(".li");
                    const $itemToggle = $e.querySelector(".acco-btn");
                    //const $itemSr = $item.querySelector(".acco-btn .sr-only");
                    const $itemBody = $e.querySelector(".acco-body");

                    if($e.classList.contains("active")) common.accordianEvent.open($item);
                    if($parent.classList.contains("is-open")) {
                        common.accordianEvent.open($item);
                    } else {
                        $itemBody.style.display = 'none';
                        //$itemSr.textContent = "펼침";
                    }

                    $itemToggle.addEventListener("click", ($el) => {
                        const $menu = $el.target.closest(".li");

                        (!$menu.classList.contains("active")) ? common.accordianEvent.open($menu) : common.accordianEvent.close($menu);
                        if(_accoAct) common.accordianEvent.reset(_list, $menu);
                    });
                });
            });
        },
        open : ($item) => {
            //const $accoSr = $item.querySelector(".acco-btn .sr-only");
            const $accoBody = $item.querySelector(".acco-body");

            $item.classList.add("active");
            $accoBody.style.display = 'block';
            //$accoSr.textContent = "접기";

            const _accoBodyH = $item.querySelector(".acco-in").scrollHeight;
            $accoBody.style.height = `${_accoBodyH+1}px`;
            setTimeout(() => {
                $accoBody.style.display = 'block';
            },0);

        },
        close : ($item) => {
            //const $accoSr = $item.querySelector(".acco-btn .sr-only");
            const $accoBody = $item.querySelector(".acco-body");

            //$accoSr.textContent = "펼침";
            $accoBody.style.height = '';
            $accoBody.style.overflow = '';
            $item.classList.remove("active");
            setTimeout(() => {
                $accoBody.style.display = 'none';
            }, 400);
        },
        reset : (_list, $menu) => {
            _list.forEach(($e) => {
                const $target = $e;
                //const $accoSr = $target.querySelector(".acco-btn .sr-only");
                const $accoBody = $target.querySelector(".acco-body");
                if(_list.indexOf($menu) !== _list.indexOf($target)) {
                    $target.classList.remove("active");
                    //$accoSr.textContent = "펼침";
                    $accoBody.style.height = '';
                    setTimeout(() => {
                        $accoBody.style.display = 'none';
                    }, 400);
                }
            });
        },
    },
}

//띠배너 스크롤 시 class 추가
function lineBnScroll() {
    const $bn = document.querySelector('#header-top');
    const $bnHeight = $bn.offsetHeight;
    const $body = document.querySelector("body");
    const scrollY = window.scrollY;
    if ($bn) {
        $body.classList.add('bn-hidden');
        if (scrollY <= $bnHeight) {
            $body.classList.remove('bn-hidden');
        }
    }
}

window.addEventListener("DOMContentLoaded", () => {
    if(comLayout.target.header !== null) {
        setTimeout(() => {
            mobGnb.init();
            comLayout.init();
			krds_pcGnb.init();
        }, 100);
    }
});

window.addEventListener("load", () => {
    setTimeout(() => {
        common.init();
    }, 100);

    if (comLayout.target.headerTop !== null) {
        setTimeout(() => {
            lineBnScroll();
        }, 200);
    }
});

window.addEventListener('scroll', () => {
    if (comLayout.target.headerTop !== null) {
        setTimeout(() => {
            lineBnScroll();
        }, 200);
    }
});


/* ** 윈도우 사이즈 체크 (반응형) ** */
let winSize;
function winSizeSet() {
	const brekpoint = 1024;
	if (window.innerWidth >= brekpoint) {
		winSize = 'pc';
	}
	else {
		winSize = 'mob';
	}
}

/* layer tab */
function layerTab() {
	const layerTabArea = document.querySelectorAll('.tab-area.layer');

	/* 탭 접근성 텍스트 세팅 */
	const tabAccText = document.createTextNode(' 선택됨');
	const tabAccTag = document.createElement('i');
	tabAccTag.setAttribute('class', 'sr-only created');
	tabAccTag.appendChild(tabAccText);

	layerTabArea.forEach(e => {
		const layerTabEle = e.querySelectorAll('.tab > ul > li');
		const tabPanel = e.querySelectorAll('.tab-conts');

		function tab() {
            layerTabEle.forEach(ele => {
                const control = ele.getAttribute('aria-controls');
                const selectedTabPanel = document.getElementById(control);

                if (ele.classList.contains('active')) {
                    const srLength = ele.getElementsByClassName('sr-only created').length;
                    if(srLength == '0')
                    {
                        //선택됨 텍스트 추가
                        ele.querySelector('button').append(tabAccTag);
                    }
                }

                ele.addEventListener('click', () => {
                    const srLength = ele.getElementsByClassName('sr-only created').length;
                    layerTabInitial(); //레이어탭 초기화
                    ele.classList.add('active');
                    if(srLength == '0')
                    {
                        ele.querySelector('button').append(tabAccTag); //선택됨 텍스트 추가
                    }
                    ele.setAttribute('aria-selected', 'true');
                    if(selectedTabPanel != null){
                        selectedTabPanel.classList.add('active');
                    }
                });
            });
        }

		//레이어탭 초기화
		function layerTabInitial() {
			layerTabEle.forEach(ele => {
				ele.classList.remove('active');
				ele.setAttribute('aria-selected', 'false');
				//ele.removeAttribute('style');
				if (ele.classList.contains('active')) {
                    const text = ele.querySelector('.sr-only.created');
                    //ele.querySelector('button').removeChild(text);
                }

			});
			tabPanel.forEach(ele => {
				ele.classList.remove('active');
				//ele.removeAttribute('style');
			})
		}
		tab();
	});
}


/*** * accordion * ***/
const $accordionBtn = document.querySelectorAll('.btn-accordion');
const kds_accordion = {
	init: () => {
		kds_accordion.expand();
	},
	expand: () => {
		$accordionBtn.forEach(e => {
			const $wrapper = e.closest('.accordion');
			const $wrapAll = $wrapper.querySelectorAll('.accordion-item');
			const $wrap = e.closest('.accordion-item');

			e.addEventListener('click', () => {
				if (!$wrap.classList.contains('active')) {
					$wrapAll.forEach(ele => {
						ele.classList.remove('active');
						ele.querySelector('.btn-accordion').classList.remove('active');
					});

					$wrap.classList.add('active');
					e.classList.add('active');
				}
				else {
					$wrap.classList.remove('active');
					e.classList.remove('active');
				}
			});

		});
	},
}

/*
const $modalTrigger = document.querySelectorAll('.open-modal');
const $modalCloseTrigger = document.querySelectorAll('.close-modal');
const $kds_body = document.querySelector('body');
const kds_modal = {
	init: () => {
		kds_modal.open();
		kds_modal.close();
	},
	open: () => {
		$modalTrigger.forEach(e => {
			e.addEventListener('click', ele => {
				const id = e.getAttribute('data-target');

				e.classList.add('modal-opened');
				e.setAttribute('tabindex', '-1');

				kds_modal.modalOpen(id);
				ele.preventDefault();
			});
		});
	},
	modalOpen: (id) => {
		const $idVal = document.getElementById(id);
		const $dialog = $idVal.querySelector('.modal-content');
		const $modalBack = $idVal.querySelector('.modal-back');
		const $modalOpened = document.querySelectorAll('.modal.in:not(.sample)');
		const $modalOpenedLen = $modalOpened.length + 1;
		$kds_body.classList.add('scroll-no');
		$idVal.setAttribute('aria-hidden', 'false');
		$modalBack.classList.add('in');
		$idVal.classList.add('shown');
		setTimeout(() => {
			$idVal.classList.add('in');
		},150);

		//열린 팝업창 포커스
		$dialog.setAttribute('tabindex', '0');

		//모달 여러개 열린경우 마지막 열린 모달 z-index높게
		if ($modalOpenedLen > 1){
			const openedLen = $modalOpenedLen;
			const zIndexNew = 1010 + openedLen;
			$idVal.setAttribute('style', 'z-index: ' + zIndexNew);
		}

		//레이어 진입 시 포커스
		setTimeout(() => {
			$dialog.focus();
		},350);
	},
	close: () => {
		$modalCloseTrigger.forEach(e => {
			e.addEventListener('click', ele => {
				const id = e.closest('.modal').getAttribute('id');
				kds_modal.modalClose(id);
			});
			e.addEventListener('keydown', ele => { //닫기버튼에서 탭 키 누르면 모달 내 첫번쨰 포커스로 키보드 이동
				if (e.classList.contains('btn-close')) {
					const keyCode = ele.keyCode || ele.which;
					if (!ele.shiftKey && keyCode == 9) {
						e.closest('.modal-content').focus();// 첫번째 링크로 이동
						ele.preventDefault();
					}
				}
			});
		});
	},
	modalClose: (id) => {
		const $idVal = document.getElementById(id);
		const $dialog = $idVal.querySelector('.modal-content');
		const $modalOpened = document.querySelectorAll('.modal.in:not(.sample)');
		const $modalOpenedLen = $modalOpened.length;
		if ($modalOpenedLen < 2) {
			$kds_body.classList.remove('scroll-no');
		}

		$idVal.setAttribute('aria-hidden', 'true');
		$idVal.classList.remove('in');

		$dialog.removeAttribute('tabindex');

		setTimeout(() => {
			$idVal.classList.remove('shown');
		},150);

		//모달 창 연 버튼에 class 삭제 및 tabindex 0로 조정 (포커스 영역 수정)
		const $triggerBtn = document.querySelector('.modal-opened');
		if ($triggerBtn != null) {
			$triggerBtn.focus();
			$triggerBtn.setAttribute('tabindex', '0');
			$triggerBtn.classList.remove('modal-opened');
		}
	},
}
*/
/*** * tooltip * ***/
const krds_tooltip = {
    init: ()=> {
        krds_tooltip.tooltipEvent();
    },
    tooltipEvent: () => {
        const _toolBtns = document.querySelectorAll(".krds-tooltip-wrap .tool-btn");

        _toolBtns.forEach(($toolBtn) => {
            const _span = document.createElement("span");
            const _txt = document.createTextNode("열기");

            _span.classList.add("sr-only");
            _span.appendChild(_txt);

            $toolBtn.innerHTML="";
            $toolBtn.appendChild(_span);

            $toolBtn.addEventListener("click", ($el) => {
                const $parent = $toolBtn.closest(".krds-tooltip-wrap");
                const $closeBtn = $parent.querySelector(".tool-close");
                const $cnt = $parent.querySelector(".tool-in");
                const $srTxt = $el.target.querySelector(".sr-only");
                if($cnt.style.display !== "block") {
                    $cnt.style.display = "block";
                    $cnt.setAttribute("tabindex", 0);
                    $srTxt.textContent = "닫기";
                    krds_tooltip.tooltipResize($parent, $cnt);
                }
                $closeBtn.addEventListener("click", () => {
                    $srTxt.textContent = "열기";
                    $cnt.style.display = "";
                    $cnt.removeAttribute("tabindex");
                    $toolBtn.focus();
                    krds_tooltip.tooltipResize($parent, $cnt);
                });

                window.addEventListener("resize", () => {
                    krds_tooltip.tooltipResize($parent, $cnt);
                });
            });
        });
    },
    tooltipResize: ($parent, $cnt) => {
        if (winSize === 'mob') {
            krds_tooltip.tooltipMob($parent, $cnt);
        } else {
            krds_tooltip.tooltipPc($cnt);
        }
        window.addEventListener('resize', () => {
            if (winSize === 'mob') {
                krds_tooltip.tooltipMob($cnt);
            } else {
                krds_tooltip.tooltipPc($cnt);
            }
        });
    },
    tooltipMob: ($parent, $cnt) => {
        const _offsetL = $parent.offsetLeft - 16;
        const _width = document.body.clientWidth;
        const _offsetR = _width - ($parent.clientWidth + _offsetL) - 32;
        if ($cnt) {
            $cnt.style.left = `-${_offsetL}px`;
            $cnt.style.right = `-${_offsetR}px`;
        }
    },
    tooltipPc: ($cnt) => {
        $cnt.style.left = '';
        $cnt.style.right = '';
    },
}

/* ** 도움말 ** */
const helperArea = document.querySelectorAll('.helper-area');
const helperBox = {
	init: () => {
		if (helperArea.length > 0) {  //해당 클래스 존재할떄만 실행
			setTimeout(() => {
				helperBox.paddingSet();
			},50);
			setTimeout(() => {
				helperBox.heightSet();
			},100);
		}
	},
	paddingSet: () => { //영역 세팅
		const bnH = document.querySelector('#header-top').offsetHeight;
		const headerH = document.querySelector('#header').offsetHeight;

		const defaultPadding = bnH + headerH;
		const bnHiddgnPadding = headerH;

		const $wrap = document.querySelector('#wrap');
		const $expandBtn = document.querySelector('.btn-helper.expand');
		const $expandBox = document.querySelector('.helper-wrap');

		const $collapseBtn = document.querySelector('.btn-helper.fold');
		if (document.body.classList.contains('bn-hidden')) { //top banner 안보임
			if ($wrap.classList.contains('scroll-down')) { //header영역 안보임
				$expandBtn.style.marginTop = '0';
				if (winSize == 'pc') {
					$expandBox.style.paddingTop = '0';
					$collapseBtn.style.marginTop = '0';
				} else {
					$expandBox.removeAttribute('style');
					$collapseBtn.removeAttribute('style');
				}
			} else { //header영역 보임
				$expandBtn.style.marginTop = bnHiddgnPadding + 'px';
				if (winSize == 'pc') {
					$expandBox.style.paddingTop = bnHiddgnPadding + 'px';
					$collapseBtn.style.marginTop = bnHiddgnPadding + 'px';
				} else {
					$expandBox.style.paddingTop = '0';
					$collapseBtn.removeAttribute('style');
				}
			}
		} else { //top banner 보임
			$expandBtn.style.marginTop = defaultPadding + 'px';
			if (winSize == 'pc') {
				$expandBox.style.paddingTop = defaultPadding + 'px';
				$collapseBtn.style.marginTop = defaultPadding + 'px';
			} else {
				$expandBox.removeAttribute('style');
				$collapseBtn.removeAttribute('style');
			}
		}

	},
	trigger: () => { //도움말열기 버튼에 추가한 class 삭제
		const btnExec = document.querySelectorAll('.btn-help-exec');
		if (helperArea.length > 0) {
			btnExec.forEach(e => {
				e.classList.remove('btn-help-clicked');
			});
		}
	},
	expand: () => { //도움말버튼 클릭 시 실행
		const btnExec = document.querySelectorAll('.btn-help-exec');
		const target = document.querySelector('.helper-wrap');
		if (helperArea.length > 0) {
			btnExec.forEach(e => {
				e.addEventListener('click', () => {
					helperBox.open();
					helperBox.trigger();
					e.classList.add('btn-help-clicked');
					setTimeout(() => {
						target.focus();
					}, 50);
				});
			});
		}

	},
	collapse: () => { //도움말 접어두기 버튼 클릭 시 실행
		const btn = document.querySelector('.btn-helper.fold');

		if (helperArea.length > 0) {
			btn.addEventListener('click', () => {
				if (winSize == 'mob') {
					document.body.classList.remove('scroll-no');
				}
				helperBox.close();
			});
		}
	},
	open: () => { //도움말 열기
		if (helperArea.length > 0) {  //해당 클래스 존재할떄만 실행
			const target = document.querySelector('.helper-wrap');
			const inner = document.querySelector('#container > .inner');
			const $header = document.querySelector("#header .head-body > .inner");
			const $container = document.querySelector("#container");
			const _width = document.body.clientWidth;
			if (winSize == 'mob') {
				document.body.classList.add('scroll-no');
			}
			target.setAttribute('aria-expanded', 'true');
			target.setAttribute('tabindex', '0');
			document.querySelector('.helper-area').classList.add('expand');

			if (inner.classList.contains('flexible')) { // 화면 사이즈 줄어들면 영역도 줄어들게
				inner.classList.remove('folded');
				$container.classList.remove('help-close');
				$container.classList.add("help-open");
				const _headerL = $header.offsetLeft;
				if( _width > 1024 && _width < 1900  ){
					$container.classList.remove("help-open");
					$container.classList.add("help-open");
					$container.style.paddingRight="";
					$container.style.paddingLeft=`${_headerL+26}px`;
				}

				helperBox.resize($header, $container);
			}
		}
	},
	close: () => { //도움말 접기
		const $header = document.querySelector("#header .head-body > .inner");
		const $container = document.querySelector('#container');
		const target = document.querySelector('.helper-wrap');
		const inner = document.querySelector('#container > .inner');
		const trigger = document.querySelectorAll('.btn-help-clicked');
		const _width = document.body.clientWidth;
		target.setAttribute('aria-expanded', 'false');
		target.removeAttribute('tabindex');
		document.querySelector('.helper-area').classList.remove('expand');

		if (trigger.length > 0) { //버튼 클릭으로 도움말 펼친경우 클릭한 버튼으로 포커스
			trigger[0].focus();
		}

		if (inner.classList.contains('flexible')) { // 도움말 닫히면 컨텐츠 영역 늘리기
			inner.classList.add('folded');
			$container.classList.add("help-close");
			$container.classList.remove("help-open");
			$container.style.paddingLeft=``;
			if ($container.classList.contains('help-close')) {
				$container.style.paddingLight=``;
				$container.style.paddingRight=``;
			} else if (_width > 1900 || _width <= 1024 ) {
				$container.classList.remove("help-open");
				$container.classList.remove("help-close");
			}
			helperBox.resize($header, $container);
		}
	},
	resize: ($header, $container) => {
		window.addEventListener("resize", () => {
			const _headerL = $header.offsetLeft;
			const _width = document.body.clientWidth;
			if ( _width > 1024 && _width < 1900) {
				$container.style.paddingRight="";
				if($container.classList.contains("help-open")) {
					$container.style.paddingLeft=`${_headerL+26}px`;
				}else {
					$container.style.paddingLeft=``;
				}
			} else if ( _width <= 1024 ) {
				$container.style.paddingLeft="";
				$container.style.paddingRight="";
			} else {
				$container.style.paddingLeft= "";
			}
		});
	},
	heightSet: () => {
		const $helperArea = document.querySelector('.helper-area');
		const $expandBox = document.querySelector('.helper-wrap');
		const $contsArea = document.querySelector('.helper-conts-area');
		const helperTitH = document.querySelector('.helper-tit').offsetHeight;

		const contsPt = parseInt(getComputedStyle($expandBox).paddingTop);
		const contsAreaH = window.innerHeight - helperTitH - contsPt;

		$contsArea.style.height = contsAreaH + 'px';

		if (winSize == 'mob') {
			if ($helperArea.classList.contains('expand')) {
				document.body.classList.add('scroll-no');
			}
		} else {
			document.body.classList.remove('scroll-no');
		}

	}
}

/* ** 영역 높이 확장 축소 ** */
function collapseBox() {
	const box = document.querySelectorAll('.conts-expand-area');
	box.forEach(e => {
		const btn = e.querySelector('.btn-conts-expand');
		if (btn != null) {
			btn.addEventListener('click', () => {
				e.classList.toggle('active');
			});
		}
	});
}

/* ** 박스형 체크박스 상태에 따른 디자인 변경 ** */
function chkBox() {
	const box = document.querySelectorAll('.chk-group-wrap');
	box.forEach(e => {
		const boxList = e.querySelectorAll('li');
		boxList.forEach(ele => {
			ele.removeAttribute('class');
			const thisList = ele.closest('li');
			const checkbox = ele.querySelector('input[type=checkbox]');
			if (checkbox != null) {
				const is_disabled = checkbox.disabled;
				let is_checked = checkbox.checked;

				if (is_disabled == true) {
					thisList.classList.add('disabled');
				}
				else {
					if (is_checked == true) {
						thisList.classList.add('checked');
					}
				}

				checkbox.addEventListener('click', () => {
					if (is_checked == true) {
						thisList.classList.remove('checked');
						is_checked = false;
					} else {
						thisList.classList.add('checked');
						is_checked = true;
					}
				});
			}

			const rdo = ele.querySelector('input[type=radio]');
			if (rdo != null) {
				const is_disabled = rdo.disabled;
				let is_checked = rdo.checked;

				if (is_disabled == true) {
					thisList.classList.add('disabled');
				}
				else {
					if (is_checked == true) {
						thisList.classList.add('checked');
					}
				}

				rdo.addEventListener('click', (e) => {
					const rdoGroup = rdo.closest('.chk-group-wrap');
					const rdoLi = rdoGroup.querySelectorAll('li');
					let is_checked2 = e.checked;
					rdoLi.forEach(ele => {
						ele.classList.remove('checked');
						is_checked2 = false;
					});
					if (is_checked2 == true) {
						thisList.classList.remove('checked');
						is_checked2 = false;
					} else {
						thisList.classList.add('checked');
						is_checked2 = true;
					}
				});
			}

		});
	});
}


/* ** 스크롤 값 체크 ** */
let scrollY = window.scrollY;
let scrollH = document.body.scrollHeight;
function scrollVal() {
	scrollY = window.scrollY;
	scrollH = document.body.scrollHeight;
}

/* ** 스크롤 네비게이션 ** */
const winHeight = window.innerHeight;
const quickIndicators = document.querySelectorAll('.quick-list');

const quickNav = {
	init: () => {
		if (quickIndicators.length > 0) { //해당 클래스 존재할떄만 실행
			quickNav.linkNav();
		}
	},
	reset: () => { //초기화
		quickIndicators.forEach(e => {
			const locationList = e.querySelectorAll('a');
			locationList.forEach(ele => {
				ele.classList.remove('active');
			});
		});
	},
	linkNav: () => { //퀵 네비게이션 클릭 시 스크롤 이동
		quickIndicators.forEach(e => {
			const locationList = e.querySelectorAll('a');
			locationList.forEach(ele => {
				const target = document.querySelector(ele.getAttribute('href'));
				const offsetY = target.getBoundingClientRect().top + scrollY;

				ele.addEventListener('click', (ev) => {
					ev.preventDefault();

					window.scrollTo({
						left: 0,
						top: offsetY,
						behavior: 'smooth',
					});
				});
			});
		});
	},
	navHighlight: () => { //페이지 스크롤 시 퀵 네비게이션 해당메뉴 active
		if (quickIndicators.length > 0) {
			const sectionArea = document.querySelectorAll('.section-link');
			const topHeight = Math.ceil(winHeight / 5);
			const firstSecTop = document.querySelectorAll('.scroll-check .section-link')[0].offsetTop;
			sectionArea.forEach(current => {
				const sectionHeight = current.offsetHeight;
				const sectionTop = current.offsetTop - topHeight;
				const sectionId = current.getAttribute("id");
				if (scrollY <= firstSecTop) { //스크롤이 첫번째 섹션보다 위에 있으면 맨 위 네비 active
					document.querySelector(".conts-area > .quick-nav-area .quick-list li:first-of-type a").classList.add("active");
				}
				else if (scrollY + winHeight >= scrollH) { //스크롤이 맨 하단에 있으면 맨 아래 네비 active
					quickNav.reset();
					document.querySelector(".conts-area > .quick-nav-area .quick-list li:last-of-type a").classList.add("active");
				}
				else {
					if (scrollY > sectionTop && scrollY <= sectionTop + sectionHeight) { //스크롤이 해당 섹션
						document.querySelector(".conts-area > .quick-nav-area a[href*=" + sectionId + "]").classList.add("active");
					} else {
						document.querySelector(".conts-area > .quick-nav-area a[href*=" + sectionId + "]").classList.remove("active");
					}
				}
			});
		}
	},
}

/* ** 스킵네비게이션 클릭 시 scroll 맨 위로 ** */
function goTop() {
	const $skip = document.querySelector('.go-top');
	$skip.addEventListener('click', () => {
		setTimeout(() => {
			window.scrollTo({
				left: 0,
				top: 0,
				behavior: 'smooth',
			});

            const logoLink= document.querySelector('.logo a');


            if(logoLink) {
                 logoLink.setAttribute('tabindex', '-1');

                 logoLink.addEventListener('focus', ()  => {
                    logoLink.style.outline = "2px solid #000";
                 }, {once: false});

                 logoLink.addEventListener('blur', ()  => {
                    logoLink.style.outline = "none";
                 }, {once: false});
                 logoLink.focus();
            }
		}, 200);
	});
}

window.addEventListener("DOMContentLoaded", () => {
	layerTab();
	kds_accordion.init();
    //kds_modal.init();
    krds_tooltip.init();

	/* ** 윈도우 사이즈 체크 (반응형) ** */
	winSizeSet();

	/* ** 영역 높이 확장 축소 ** */
	collapseBox();

	/* ** 박스형 체크박스 상태에 따른 디자인 변경 ** */
	chkBox();

	/* ** 스크롤 네비게이션 ** */
	quickNav.init();

	/* ** 스킵네비게이션 클릭 시 scroll 맨 위로 ** */
	if(document.querySelector('.go-top') !== null) goTop();

	setTimeout(() => { //gnb footer 등 include영역으로 로딩시간이 필요한경우 settimeout에 넣어줌 (배포시 삭제필요)
		/* ** 도움말 ** */
		helperBox.init();
		if (winSize == 'pc') {
			helperBox.open();
		}

		//클릭이벤트는 로드시에만 실행시키기
		helperBox.expand();
		helperBox.collapse();
	}, 200);
});


window.addEventListener('scroll', () => {
	/* ** 스크롤 값 체크 ** */
	scrollVal();

	/* ** 스크롤 네비게이션 ** */
	//quickNav.navHighlight();

	setTimeout(() => { //gnb footer 등 include영역으로 로딩시간이 필요한경우 settimeout에 넣어줌 (배포시 삭제필요)
		/* ** 도움말 ** */
		helperBox.init();
	}, 200);
});

window.addEventListener('resize', () => {
	/* ** 윈도우 사이즈 체크 (반응형) ** */
	winSizeSet();

	/* ** 도움말 ** */
	helperBox.init();
});