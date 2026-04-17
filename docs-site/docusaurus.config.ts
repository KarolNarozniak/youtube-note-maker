import type {Config} from "@docusaurus/types";
import type * as Preset from "@docusaurus/preset-classic";
import {themes as prismThemes} from "prism-react-renderer";

const config: Config = {
  title: "Thothscribe",
  tagline: "Local YouTube, web, and notes to RAG context.",
  favicon: "img/logo.png",
  url: "http://127.0.0.1:3000",
  baseUrl: "/",
  organizationName: "local",
  projectName: "thothscribe",
  onBrokenLinks: "throw",
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: "warn",
    },
  },
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },
  presets: [
    [
      "classic",
      {
        docs: {
          sidebarPath: "./sidebars.ts",
        },
        blog: false,
        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],
  themeConfig: {
    image: "img/logo.png",
    navbar: {
      title: "Thothscribe",
      logo: {
        alt: "Thothscribe logo",
        src: "img/logo.png",
      },
      items: [
        {
          type: "docSidebar",
          sidebarId: "guideSidebar",
          position: "left",
          label: "Docs",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Systems",
          items: [
            {label: "Architecture", to: "/docs/architecture"},
            {label: "API", to: "/docs/api"},
            {label: "Operations", to: "/docs/operations"},
          ],
        },
        {
          title: "Run Locally",
          items: [
            {label: "Setup", to: "/docs/setup"},
            {label: "Development", to: "/docs/development"},
          ],
        },
      ],
      copyright: `Built for local-first research with Thothscribe.`,
    },
    colorMode: {
      defaultMode: "light",
      respectPrefersColorScheme: true,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
