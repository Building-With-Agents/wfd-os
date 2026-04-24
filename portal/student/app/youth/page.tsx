"use client"

import {
  Compass, ArrowRight, Heart, GraduationCap, Code, Briefcase,
  Users, Award, MapPin, Calendar, Clock, CheckCircle2, ExternalLink,
  Laptop, BookOpen, Target, Mail,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import NewsletterSubscribe from "@/components/newsletter-subscribe"

function NavBar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <a href="/" className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Compass className="h-4.5 w-4.5 text-primary-foreground" />
          </div>
          <span className="text-lg font-bold text-foreground">Computing for All</span>
        </a>
        <div className="hidden items-center gap-6 md:flex">
          <a href="/cfa/ai-consulting" className="text-sm text-muted-foreground hover:text-foreground">AI Consulting</a>
          <a href="/youth" className="text-sm font-medium text-foreground">Youth Program</a>
          <a href="/coalition" className="text-sm text-muted-foreground hover:text-foreground">Coalition</a>
          <a href="/#about" className="text-sm text-muted-foreground hover:text-foreground">About</a>
          <a href="https://secure.givelively.org/donate/computing-for-all" target="_blank" rel="noopener noreferrer">
            <Button size="sm" variant="outline" className="gap-1">
              <Heart className="h-3.5 w-3.5" /> Donate
            </Button>
          </a>
        </div>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="bg-gradient-to-b from-primary/5 via-primary/3 to-background px-4 py-16 sm:py-24">
      <div className="mx-auto max-w-4xl text-center">
        <Badge className="mb-4 bg-primary/10 text-primary border-primary/20">
          Grant-funded program &middot; Ages 16-24 &middot; Washington State
        </Badge>
        <h1 className="text-4xl font-bold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
          Tech Career Bridge
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
          Learn to code at Computing for All. Full Stack Web &amp; Software Development training
          that takes you from zero to job-ready in six levels.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <a href="https://cfaeducation.powerappsportals.com/enrollment-form/" target="_blank" rel="noopener noreferrer">
            <Button size="lg" className="gap-2 ">
              Ready to apply? <ArrowRight className="h-4 w-4" />
            </Button>
          </a>
          <a href="#curriculum">
            <Button size="lg" variant="outline" className="gap-2">
              See the curriculum
            </Button>
          </a>
        </div>
      </div>
    </section>
  )
}

function Intro() {
  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="mb-4 text-2xl font-bold text-foreground sm:text-3xl">
          Your Career Bridge
        </h2>
        <p className="text-lg text-muted-foreground">
          Computing for All offers a <strong className="text-foreground">Full Stack Web &amp; Software Development
          Tech Career Bridge</strong> program (formerly Pre-Apprenticeship) for Washington state students.
        </p>
        <p className="mt-4 text-muted-foreground">
          Tech Career Bridge is a training program to provide you with the technical and professional
          skills to qualify for industry internships, and entry level jobs.
        </p>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 md:grid-cols-4">
          {[
            { icon: Code, label: "Industry-aligned Coding Instruction" },
            { icon: Briefcase, label: "Professional Skills Development" },
            { icon: Users, label: "Industry Mentorship & Networking" },
            { icon: Target, label: "Competitive Candidate Positioning" },
          ].map((item) => (
            <div key={item.label} className="flex flex-col items-center text-center">
              <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <item.icon className="h-5 w-5 text-primary" />
              </div>
              <p className="text-xs font-medium text-foreground">{item.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Benefits() {
  const benefits = [
    {
      icon: BookOpen,
      title: "Portfolio Creation",
      description:
        "Our curriculum is project-based. This means you'll be coding functional web applications as you learn. You'll also be using professional software, versioning, and design tools. Upon completion of the program, you should have a portfolio of projects to show to potential employers.",
    },
    {
      icon: Award,
      title: "Certification",
      description:
        "Our curriculum will prepare you to complete industry certification tests such as those offered by Microsoft and other companies. You may also earn college credit.",
    },
    {
      icon: Briefcase,
      title: "Job Skills",
      description:
        "The Tech Career Bridge pathway teaches both technical and job skills, including resume, portfolio, and interview preparation. You'll learn to use professional project management tools, practice teamwork, and leadership skills.",
    },
    {
      icon: Users,
      title: "Mentorship",
      description:
        "You will meet professionals from Seattle area tech companies who volunteer as guest speakers or coaches. Some employer mentors work directly with students, creating, assigning, and reviewing completed projects.",
    },
    {
      icon: Target,
      title: "Career Navigation",
      description:
        "Throughout the program, CFA will help guide your next steps, should you wish to pursue an internship, a formal tech apprenticeship, or entry into a post secondary education. After graduating from the program we will follow up with you to further support you on your career path.",
    },
  ]
  return (
    <section className="bg-slate-50 px-4 py-16">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-10 text-center text-2xl font-bold text-foreground sm:text-3xl">
          Program Benefits
        </h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {benefits.map((b) => (
            <Card key={b.title} className="p-6">
              <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <b.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mb-2 font-semibold text-foreground">{b.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{b.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function ProgramDetails() {
  const details = [
    "Live, online instruction in a virtual classroom, led by industry-experienced instructors",
    "Grant-funded program for qualified students",
    "Connected with Seattle earn-to-learn programs",
    "Advanced placement tests for students with prior programming experience",
    "Some assistance available for computer equipment",
  ]
  return (
    <section className="px-4 py-16">
      <div className="mx-auto max-w-3xl">
        <h2 className="mb-8 text-center text-2xl font-bold text-foreground sm:text-3xl">
          Program Details
        </h2>
        <Card className="p-6">
          <ul className="space-y-3">
            {details.map((d) => (
              <li key={d} className="flex items-start gap-3">
                <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
                <span className="text-sm text-foreground">{d}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </section>
  )
}

function ReadyToApplyMidCTA() {
  return (
    <section className="px-4 py-12">
      <div className="mx-auto max-w-3xl">
        <Card className="border-primary/20 bg-primary/5 p-8 text-center">
          <h3 className="text-2xl font-bold text-foreground sm:text-3xl">Ready to Apply?</h3>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Start your tech career journey today. Applications are open for the upcoming quarters.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-4">
            <a href="#apply">
              <Button size="lg" className="gap-2">
                Apply Now <ArrowRight className="h-4 w-4" />
              </Button>
            </a>
          </div>
        </Card>
      </div>
    </section>
  )
}

function Schedule() {
  return (
    <section className="bg-slate-50 px-4 py-16">
      <div className="mx-auto max-w-5xl">
        <h2 className="mb-10 text-center text-2xl font-bold text-foreground sm:text-3xl">
          Schedule
        </h2>
        <div className="grid gap-6 md:grid-cols-2">
          <Card className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              <h3 className="font-semibold text-foreground">Fall, Winter &amp; Spring (school year)</h3>
            </div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>8 weeks</span>
              </li>
              <li className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>2 classes per week: Tuesdays &amp; Thursdays</span>
              </li>
              <li className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>2.75 hours per class, 4:00 PM &ndash; 6:45 PM</span>
              </li>
            </ul>
          </Card>
          <Card className="p-6">
            <div className="mb-3 flex items-center gap-2">
              <Calendar className="h-5 w-5 text-primary" />
              <h3 className="font-semibold text-foreground">Summer quarter (2 courses)</h3>
            </div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>7-8 weeks</span>
              </li>
              <li className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>4 classes per week: Monday-Thursday</span>
              </li>
              <li className="flex items-start gap-2">
                <Clock className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>5 hours per class, Noon &ndash; 5:00 PM</span>
              </li>
            </ul>
          </Card>
        </div>

        <Card className="mt-6 border-primary/20 bg-primary/5 p-6">
          <h3 className="mb-3 font-semibold text-foreground">Upcoming Quarters</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-primary" />
              <span className="text-sm text-foreground">
                <strong>Spring 2026:&nbsp;</strong>March 31 &ndash; May 26
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4 text-primary" />
              <span className="text-sm text-foreground">
                <strong>Summer 2026:&nbsp;</strong>July 1 &ndash; August 13
              </span>
            </div>
          </div>
        </Card>
      </div>
    </section>
  )
}

function Curriculum() {
  const levels = [
    {
      num: 1,
      title: "Intro to Computer Programming with Python",
      description:
        "Learn the basics of computer programming with Python. By the end of the quarter, students work in teams to design and code a Python game.",
    },
    {
      num: 2,
      title: "Web Development 1: HTML & CSS",
      description: "Learn to code a website, and explore the basics of user interface design.",
    },
    {
      num: 3,
      title: "Web Development 2: JavaScript",
      description:
        "Learn the programming language of the web while continuing to advance your HTML and CSS skills.",
    },
    {
      num: 4,
      title: "Frontend Web Development",
      description:
        "Advance your understanding of HTML, CSS, and JavaScript while creating interactive websites with functional forms, and API-generated content.",
    },
    {
      num: 5,
      title: "Backend Web Development",
      description:
        "Use Python and JavaScript for server side programs for dynamic content generation and learn SQL and no-SQL database management.",
    },
    {
      num: 6,
      title: "Full Stack Web Development",
      description:
        "Use server side Node JS and frontend framework React JS (MERN stack) to create a modern, full stack web application.",
    },
    {
      num: 7,
      title: "The Last Mile (Optional) — Industry-Mentored Full Stack Web Development",
      description:
        "Build a full stack application directed under the tutelage of one of our Employer Partners or an industry volunteer. Network and add to your portfolio.",
      optional: true,
    },
  ]
  return (
    <section id="curriculum" className="px-4 py-16">
      <div className="mx-auto max-w-4xl">
        <h2 className="mb-3 text-center text-2xl font-bold text-foreground sm:text-3xl">
          Curriculum
        </h2>
        <p className="mb-10 text-center text-muted-foreground">
          Six levels from zero to full stack. Plus an optional industry-mentored capstone.
        </p>
        <div className="space-y-3">
          {levels.map((level) => (
            <Card
              key={level.num}
              className={`p-5 ${level.optional ? "border-amber-200 bg-amber-50/40" : ""}`}
            >
              <div className="flex gap-4">
                <div
                  className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                    level.optional
                      ? "bg-amber-100 text-amber-700"
                      : "bg-primary/10 text-primary"
                  }`}
                >
                  {level.num}
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-foreground">
                      Level {level.num}: {level.title}
                    </h3>
                    {level.optional && (
                      <Badge className="bg-amber-100 text-amber-700 border-amber-200 text-xs">
                        Optional
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">{level.description}</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

function Requirements() {
  return (
    <section className="bg-primary px-4 py-16 text-primary-foreground">
      <div className="mx-auto max-w-3xl text-center">
        <h2 className="mb-4 text-2xl font-bold sm:text-3xl">Tech Career Bridge Requirements</h2>
        <p className="mb-8 text-primary-foreground/80">To qualify, you must be:</p>
        <div className="grid gap-4 sm:grid-cols-3">
          {[
            { icon: MapPin, title: "Washington State", description: "Washington state resident" },
            { icon: Users, title: "Ages 16-24", description: "Between 16 and 24 years old" },
            { icon: Heart, title: "Financial Assistance", description: "In need of financial assistance" },
          ].map((r) => (
            <div key={r.title} className="rounded-lg bg-primary-foreground/10 p-5 backdrop-blur">
              <r.icon className="mx-auto mb-2 h-6 w-6" />
              <h3 className="font-semibold">{r.title}</h3>
              <p className="mt-1 text-sm text-primary-foreground/80">{r.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Apply() {
  return (
    <section id="apply" className="px-4 py-16">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="mb-4 text-2xl font-bold text-foreground sm:text-3xl">Ready to apply?</h2>
        <p className="mb-8 text-muted-foreground">
          Start your tech career journey today. Applications are open for the upcoming quarters.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <a href="https://cfaeducation.powerappsportals.com/enrollment-form/" target="_blank" rel="noopener noreferrer">
            <Button size="lg" className="gap-2 ">
              <ExternalLink className="h-4 w-4" /> Apply now
            </Button>
          </a>
          <a
            href="https://www.computingforall.org/tech-career-bridge/"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button size="lg" variant="outline" className="gap-2">
              Visit original page <ExternalLink className="h-4 w-4" />
            </Button>
          </a>
        </div>
      </div>
    </section>
  )
}

function SupportStudents() {
  return (
    <section className="bg-slate-50 px-4 py-16">
      <div className="mx-auto max-w-2xl text-center">
        <Heart className="mx-auto mb-4 h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold text-foreground sm:text-3xl">Support our Students</h2>
        <p className="mt-3 text-muted-foreground">
          Your donation helps us provide free coding education, laptops, and mentorship to young
          people across Washington State who want to build a career in technology.
        </p>
        <a
          href="https://secure.givelively.org/donate/computing-for-all"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button size="lg" className="mt-6 gap-2 ">
            <Heart className="h-4 w-4" /> Donate to Computing for All
          </Button>
        </a>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border bg-white py-10">
        <NewsletterSubscribe />
      <div className="mx-auto max-w-5xl px-4">
        <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <Compass className="h-5 w-5 text-primary" />
            <span className="font-semibold text-foreground">Computing for All</span>
            <span className="text-xs text-muted-foreground">
              | 501(c)(3) nonprofit | Bellevue, WA
            </span>
          </div>
          <div className="flex flex-wrap justify-center gap-4 text-sm text-muted-foreground">
            <a href="/" className="hover:text-foreground">Home</a>
            <a href="/coalition" className="hover:text-foreground">Coalition</a>
            <a href="/cfa/ai-consulting" className="hover:text-foreground">AI Consulting</a>
            <a href="mailto:info@computingforall.org" className="hover:text-foreground">Contact</a>
          </div>
        </div>
        <Separator className="my-6" />
        <p className="text-center text-xs text-muted-foreground">
          &copy; 2026 Computing for All. All rights reserved.
        </p>
      </div>
    </footer>
  )
}

export default function YouthProgramPage() {
  return (
    <div className="min-h-screen bg-white">
      <NavBar />
      <Hero />
      <Intro />
      <Benefits />
      <ProgramDetails />
      <ReadyToApplyMidCTA />
      <Schedule />
      <Curriculum />
      <Requirements />
      <Apply />
      <SupportStudents />
      <Footer />
    </div>
  )
}
