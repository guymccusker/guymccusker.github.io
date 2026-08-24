;;; publish.el --- org-publish configuration for guymccusker.github.io  -*- lexical-binding: t; -*-
;;
;; Usage (from repo root):
;;   emacs --batch -l publish.el --eval '(org-publish "site" t)'
;;
;; This builds the org-mode sources in content/ into static HTML under
;; public/, and copies assets/ and talks/ across unchanged. No external
;; packages beyond what ships with a recent Emacs (org-mode >= 9.5) are
;; required.

(require 'org)
(require 'ox-publish)

(setq org-export-with-section-numbers nil
      org-export-with-toc nil
      org-export-with-author nil
      org-export-with-email nil
      org-export-time-stamp-file nil
      make-backup-files nil)

(defconst site-html-head
  "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
<link rel=\"stylesheet\" href=\"assets/css/style.css\">")

(defun site/preamble (_plist)
  "Simple site-wide navigation bar."
  "<nav class=\"site-nav\">
  <a href=\"index.html\">Home</a>
  <a href=\"publications.html\">Publications</a>
</nav>")

(defun site/postamble (_plist)
  "<p>Guy McCusker, Department of Computer Science, University of Bath.</p>")

(setq org-publish-project-alist
      `(("site-pages"
         :base-directory "content"
         :base-extension "org"
         :publishing-directory "public"
         :publishing-function org-html-publish-to-html
         ;; Real pages live flat in content/; #+INCLUDE fragments live one
         ;; level down in content/inc/. Keeping this non-recursive means
         ;; new fragment files never need to be added to an exclude list —
         ;; they're just invisible to the publisher by construction.
         :recursive nil
         :html-head-include-default-style nil
         :html-head-include-scripts nil
         :html-head ,site-html-head
         :html-preamble site/preamble
         :html-postamble site/postamble
         :section-numbers nil
         :with-toc nil)

        ("site-assets"
         :base-directory "assets"
         :base-extension "css\\|js\\|png\\|jpe?g\\|gif\\|svg\\|woff2?\\|ico\\|pdf"
         :publishing-directory "public/assets"
         :publishing-function org-publish-attachment
         :recursive t)

        ("site-talks"
         :base-directory "talks"
         :base-extension "html\\|css\\|js\\|png\\|jpe?g\\|gif\\|svg\\|pdf\\|org\\|txt\\|json"
         :publishing-directory "public/talks"
         :publishing-function org-publish-attachment
         :recursive t)

        ("site" :components ("site-pages" "site-assets" "site-talks"))))

(provide 'publish)
;;; publish.el ends here
